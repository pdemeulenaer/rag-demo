# src/api/rag/retrieval.py
import os
import instructor
from groq import Groq
from pydantic import BaseModel, ValidationError
import json
import cohere
from qdrant_client import QdrantClient
import logging
import redis
import pickle
from time import monotonic

from src.api.core.config import config
from src.api.core.clients import openai_client
from src.api.observability.tracing import observe, observation, trace_attributes, update_span
from src.api.rag.utils.utils import prompt_template_config
from src.api.rag.summarize import summarize_text
from src.api.api.models import Source
from src.api.rag.answer_contracts import RAGClaim, RAGGenerationResponse
from src.api.rag.modes.agentic.answering import AgenticStructuredOutputError, generate_agentic_answer
from src.api.rag.search import search_points
from src.api.rag.contracts import FederatedRetrievalScope, RetrievalScope
from src.api.rag.tools.chunk_search import search_chunks
from src.api.rag.tools.paper_search import quoted_context_papers, resolve_quoted_papers


logger = logging.getLogger(__name__)
cohere_client = cohere.Client(config.COHERE_API_KEY)

# Initialize the conversation memory
redis_client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)


def titles_by_author(author, year=None):
    if not author:
        return []

class ConversationMemory:
    def __init__(self, window_size=10): # 10 messages, i.e. 5 question-answer turns
        self.recent_messages = []
        self.full_history = [] 
        self.summary = ""
        self.window_size = window_size


@observe(name="summarize_conversation")
def summarize_conversation(messages): #, summarizer_llm):
    """
    Summarizes the conversation history using the given LLM client (Groq in this case).
    This version works without Instructor's create_with_completion.
    """
    # Convert messages list to a readable string
    formatted_messages = "\n".join(
        [f"{m['role'].capitalize()}: {m['content']}" for m in messages]
    )

    response = summarize_text(
        formatted_messages,
        provider='groq',
        model=config.SUMMARIZATION_MODEL,
        temperature=config.SUMMARIZATION_MODEL_TEMPERATURE,
        max_tokens=config.SUMMARIZATION_MODEL_MAX_TOKENS,
        template_name="summarize_conversation")

    return response.summary.strip()


def get_memory(session_id: str) -> ConversationMemory:

    # If in evaluation mode, return a fresh memory each time
    if os.getenv("EVALUATION_MODE") == "true":
        return ConversationMemory()

    # Try to get the memory object from Redis
    pickled_memory = redis_client.get(session_id)
    if pickled_memory:
        # If it exists, deserialize and return it
        return pickle.loads(pickled_memory)
    else:
        # If not, create a new one, store it, and return it
        new_memory = ConversationMemory()
        # Set a timeout for the session (e.g., 1 hour = 3600 seconds)
        redis_client.setex(session_id, 3600, pickle.dumps(new_memory))
        return new_memory


def add_message(session_id: str, role: str, content: str): #, summarizer_llm):
    memory = get_memory(session_id)

    # Add message to both lists
    memory.recent_messages.append({"role": role, "content": content})
    memory.full_history.append({"role": role, "content": content})

    # Summarize older messages if buffer exceeded
    if len(memory.recent_messages) > memory.window_size:
        # Get messages to summarize (all but the most recent)
        old_messages = memory.recent_messages[:-memory.window_size]
        summary_update = summarize_conversation(old_messages) #, summarizer_llm)
        memory.summary += " " + summary_update
        # Keep only the most recent messages in the buffer
        memory.recent_messages = memory.recent_messages[-memory.window_size:]

    # After updating memory, save it back to Redis
    session_time_to_live = 3600  # 1 hour
    redis_client.setex(session_id, session_time_to_live, pickle.dumps(memory))        


def get_embedding(text, model=config.EMBEDDING_MODEL):
    response = openai_client().embeddings.create(
        input=[text],
        model=model,
    )
    return response.data[0].embedding


@observe(name="retrieve_context", as_type="retriever", capture_input=False, capture_output=False)
def retrieve_context(query, qdrant_client, top_k=5, mode="hybrid", collection=None, scope=None):
    update_span(input={"query": query}, metadata={"mode": mode, "top_k": top_k,
        "collection": collection or config.QDRANT_COLLECTION_NAME})
    if scope is None:
        from src.api.api.papers_router import active_corpus
        from src.api.papers.consistency import active_filter
        _, active, _ = active_corpus("uploads")
        if not active:
            return []
        target_collection = collection or config.QDRANT_COLLECTION_NAME
        scope = RetrievalScope.from_builds(
            target_collection, active, filter_override=active_filter(active)
        )
    query_embedding = None if mode == "sparse" else get_embedding(query)

    if isinstance(scope, FederatedRetrievalScope):
        if collection is not None:
            raise ValueError("A federated corpus cannot be forced into one collection")
        candidates = []
        for child_scope in scope.scopes:
            candidates.extend(search_chunks(
                qdrant_client, child_scope, query=query, vector=query_embedding,
                limit=top_k, mode=mode,
            ))
        # Both collections use the same vector models and distance/fusion setup,
        # so their scores are comparable. Stable tie-breakers keep runs reproducible.
        candidates.sort(key=lambda row: (
            -(row.score if row.score is not None else float("-inf")),
            row.collection,
            row.id,
        ))
        retrieved_context = [row.model_dump() for row in candidates[:top_k]]
        update_span(output={"point_ids": [row["id"] for row in retrieved_context]},
                    metadata={"result_count": len(retrieved_context),
                              "collections": list(scope.collections)})
        return retrieved_context

    if isinstance(scope, RetrievalScope):
        target_collection = collection or scope.collection
        if target_collection != scope.collection:
            raise ValueError("Retrieval collection does not match the explicit corpus scope")
        retrieved_context = [row.model_dump() for row in search_chunks(
            qdrant_client, scope, query=query, vector=query_embedding,
            limit=top_k, mode=mode,
        )]
        update_span(output={"point_ids": [row["id"] for row in retrieved_context]},
                    metadata={"result_count": len(retrieved_context)})
        return retrieved_context

    results = search_points(qdrant_client, collection or config.QDRANT_COLLECTION_NAME,
                           query_embedding, query, top_k, mode, scope)

    retrieved_context = []
    for result in results.points:
        logger.info("Qdrant payload keys: %s", result.payload.keys())

        # payload is a dict, so we can use .get() safely
        payload = result.payload
        
        retrieved_context.append({
            "id": str(result.id),
            "text": payload["text"],
            "title": payload.get("file_title"),
            "paper_id": payload.get("paper_id"),
            "arxiv_id": payload.get("arxiv_id"),
            "paper_version": payload.get("paper_version"),
            "source_url": payload.get("source_url"),
            "authors": payload.get("authors"),
            "year": payload.get("year"),
            "page": payload.get("page_number"),
            "score": result.score,
            "type": payload.get("type", "text"),  # 'text' or 'figure'
            "image_path": payload.get("image_path"), # Only present if type='figure'
            "caption": payload.get("caption")        # Important for UI display
        })        

    update_span(output={"point_ids": [row["id"] for row in retrieved_context]},
                metadata={"result_count": len(retrieved_context)})
    return retrieved_context


class RerankedContext(list):
    """List-compatible rerank result carrying safe candidate-selection diagnostics."""

    def __init__(self, values: list[dict], diagnostics: dict):
        super().__init__(values)
        self.diagnostics = diagnostics


@observe(name="rerank_context", as_type="span", capture_input=False, capture_output=False)
def rerank_context(query: str, retrieved_context: list, top_n: int = 5):
    """
    Reranks the retrieved context chunks using Cohere's reranker.
    """

    if not retrieved_context:
        return RerankedContext([], {
            "candidate_count": 0, "selected_count": 0,
            "candidate_paper_ids": [], "selected_paper_ids": [],
            "named_paper_ids": [], "named_paper_titles": [],
            "reserved_candidate_ids": [],
            "named_paper_diversity_guard_applied": False,
            "ranked_candidates": [],
        })
    docs = [c["text"] for c in retrieved_context]

    response = cohere_client.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=docs,
        # Persist the full candidate ordering so cross-paper diversity loss can
        # be distinguished from candidate-generation failure.
        top_n=len(docs),
    )

    # Map reranked results back to original retrieved_context items
    ranked_candidates = []
    for r in response.results:
        doc_idx = r.index
        doc_score = r.relevance_score
        chunk = retrieved_context[doc_idx]
        ranked = {
            **chunk,
            "rerank_score": doc_score
        }
        ranked_candidates.append(ranked)
    # A chunk-level cross-encoder can rank many passages from one paper above every
    # passage from another explicitly requested paper. Reserve the best passage from
    # each full title quoted in the question, then fill the remaining slots by the
    # Cohere ordering. Ordinary queries retain the unmodified global top-k.
    named_papers = quoted_context_papers(query, ranked_candidates)
    named_keys = [str(row.get("paper_id") or f"title:{row['title']}")
                  for row in named_papers]
    reserved_indexes = set()
    reserved_ids = []
    for key in named_keys:
        for index, row in enumerate(ranked_candidates):
            row_key = str(row.get("paper_id") or f"title:{row.get('title')}")
            if row_key == key:
                reserved_indexes.add(index)
                reserved_ids.append(str(row.get("id")))
                break
    selected_indexes = set(reserved_indexes)
    selection_limit = max(top_n, len(reserved_indexes))
    for index in range(len(ranked_candidates)):
        if len(selected_indexes) >= selection_limit:
            break
        selected_indexes.add(index)
    reranked = [row for index, row in enumerate(ranked_candidates)
                if index in selected_indexes]
    naive_ids = [str(row.get("id")) for row in ranked_candidates[:selection_limit]]
    selected_ids = [str(row.get("id")) for row in reranked]

    candidate_papers = sorted({str(row.get("paper_id")) for row in retrieved_context
                               if row.get("paper_id")})
    selected_papers = sorted({str(row.get("paper_id")) for row in reranked
                              if row.get("paper_id")})
    diagnostics = {
        "candidate_count": len(retrieved_context),
        "selected_count": len(reranked),
        "candidate_paper_ids": candidate_papers,
        "selected_paper_ids": selected_papers,
        "candidate_paper_count": len(candidate_papers),
        "selected_paper_count": len(selected_papers),
        "named_paper_ids": [row["paper_id"] for row in named_papers if row["paper_id"]],
        "named_paper_titles": [row["title"] for row in named_papers],
        "reserved_candidate_ids": reserved_ids,
        "named_paper_diversity_guard_applied": selected_ids != naive_ids,
        "ranked_candidates": [{
            "id": str(row.get("id")), "paper_id": row.get("paper_id"),
            "title": row.get("title"), "rerank_score": row.get("rerank_score"),
        } for row in ranked_candidates],
    }

    update_span(input={"query": query, "candidate_ids": [row["id"] for row in retrieved_context]},
                output={"point_ids": [row["id"] for row in reranked]},
                metadata={"model": "rerank-english-v3.0", "top_n": top_n,
                          "candidate_paper_count": len(candidate_papers),
                          "selected_paper_count": len(selected_papers),
                          "named_paper_count": len(named_papers),
                          "named_paper_diversity_guard_applied": selected_ids != naive_ids})
    return RerankedContext(reranked, diagnostics)


def optional_int(value: object) -> int | None:
    """Return an integer metadata value, or None for absent/non-numeric values."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def process_context(context):
    lines = []
    for id, chunk in zip(context["retrieved_context_ids"], context["retrieved_context"]):
        lines.append(f"\n\n DOC ID: {id}; DOC TEXT: {chunk}\n\n---")
    return "\n".join(lines)


class InvalidCitationIdsError(ValueError):
    """The answer cited an unavailable or duplicate retrieved context ID."""

    def __init__(self, code: str = "invalid_context_ids"):
        self.code = code
        super().__init__(code)


class MissingRequiredCitationError(ValueError):
    """The answer omitted every available chunk from a required paper."""

    def __init__(self, code: str = "missing_required_citation"):
        self.code = code
        super().__init__(code)


# Keep the prompt, provider request and local parser on one schema.
OUTPUT_SCHEMA = RAGGenerationResponse.model_json_schema()


def build_prompt(context, question, session_id):
    memory = get_memory(session_id)

    formatted_recent = "\n".join(
        [f"{msg['role'].capitalize()}: {msg['content']}" for msg in memory.recent_messages]
    )

    full_history = f"Conversation Summary:\n{memory.summary.strip()}\n\nRecent Messages:\n{formatted_recent}"

    processed_context = process_context(context)

    # Extract the prompt template
    prompt_template = prompt_template_config(config.RAG_PROMPT_TEMPLATE_PATH, "rag_generation")

    system_prompt = prompt_template["system"].render(
        conversation_history=full_history,
        processed_context=processed_context,
        question=question,
        output_json_schema=json.dumps(OUTPUT_SCHEMA, indent=2)
    )

    user_prompt = prompt_template["user"].render(
        conversation_history=full_history,
        processed_context=processed_context,
        question=question,
        output_json_schema=json.dumps(OUTPUT_SCHEMA, indent=2)
    )

    logger.info(f"Prompt length: {len(system_prompt) + len(user_prompt)}")

    # For LLM call
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    return messages


class RAGUsedContext(BaseModel):
    id: str #int # changed from Aurimas' code since here we use uuid as strings
    description: str

class RAGSummarizationResponse(BaseModel):
    summary: str    


# def is_openai_model(model_name: str) -> bool:
#     """
#     Decide provider by simple naming convention.
#     Adjust if you add custom prefixes.
#     """
#     model_name = model_name.lower()
#     return model_name.startswith("gpt-") or model_name.startswith("o1-") or model_name.startswith("openai-")

def is_openai_model(model_name: str) -> bool:
    """
    Decide provider by simple naming convention.
    Excludes OSS variants (openai/gpt-oss-...) hosted on Groq.
    """
    model_name = model_name.lower()
    
    # Check for the exclusion prefix first
    if model_name.startswith("openai/gpt-oss-"):
        return False
        
    return (
        model_name.startswith("gpt-") or 
        model_name.startswith("o1-") or 
        model_name.startswith("openai-")
    )


def _validate_context_ids(response, allowed_context_ids, required_context_groups=None):
    """Baseline citation checks. Agentic reviews claims in agentic/answering.py."""
    selected = response.retrieved_context_ids
    for claim in response.claims:
        if (not claim.cited_context_ids
                or len(claim.cited_context_ids) != len(set(claim.cited_context_ids))):
            raise InvalidCitationIdsError("duplicate_or_empty_claim_citations")
    if allowed_context_ids is not None:
        allowed = {str(value) for value in allowed_context_ids}
        if not set(selected).issubset(allowed):
            raise InvalidCitationIdsError("unknown_context_id")
    selected_ids = set(selected)
    for context_ids in (required_context_groups or {}).values():
        if context_ids and selected_ids.isdisjoint({str(value) for value in context_ids}):
            raise MissingRequiredCitationError("missing_required_source_group")
    for claim in response.claims:
        if claim.need_ids:
            raise InvalidCitationIdsError("unexpected_claim_need_ids")
    return response


def _required_citation_groups(question: str, contexts: list[dict],
                              required_paper_ids=()) -> dict[str, set[str]]:
    """Map named papers to available chunk IDs for baseline citation validation."""
    groups = {}
    named_papers = quoted_context_papers(question, contexts)
    known_ids = {str(value) for value in required_paper_ids if value}
    for paper_id in known_ids:
        matching = next((row for row in contexts
                         if str(row.get("paper_id") or "") == paper_id), None)
        if matching:
            named_papers.append({"paper_id": paper_id,
                                 "title": str(matching.get("title") or paper_id)})
    seen_papers = set()
    for paper in named_papers:
        paper_id = paper.get("paper_id")
        title = str(paper["title"])
        paper_key = str(paper_id or f"title:{title}")
        if paper_key in seen_papers:
            continue
        seen_papers.add(paper_key)
        ids = {
            str(row["id"])
            for row in contexts
            if ((paper_id and str(row.get("paper_id") or "") == paper_id)
                or (not paper_id and str(row.get("title") or "") == title))
        }
        if ids:
            groups[title] = ids
    return groups


def _resolve_required_papers(catalogue, scope, question: str):
    """Resolve full quoted titles across every collection in the request scope."""
    if catalogue is None or not isinstance(scope, (RetrievalScope, FederatedRetrievalScope)):
        return []
    child_scopes = scope.scopes if isinstance(scope, FederatedRetrievalScope) else (scope,)
    resolved = []
    for child_scope in child_scopes:
        resolved.extend(resolve_quoted_papers(catalogue, child_scope, question))
    unique = {row.build_id: row for row in resolved}
    return sorted(unique.values(), key=lambda row: (row.title.casefold(), row.build_id))


def _missing_required_papers(required_papers, contexts: list[dict]):
    covered_build_ids = {str(row.get("build_id") or "") for row in contexts}
    return [paper for paper in required_papers if paper.build_id not in covered_build_ids]


def _coverage_abstention(question: str, retrieved_context: list[dict], *, agent_run,
                         retrieval_diagnostics, required_papers, missing_papers) -> dict:
    """Return evidence and diagnostics without asking a model to bridge a missing paper."""
    diagnostics = {
        "status": "safe_abstention",
        "reason": "named_paper_coverage_failed",
        "required_paper_count": len(required_papers),
        "missing_build_ids": [paper.build_id for paper in missing_papers],
        "missing_titles": [paper.title for paper in missing_papers],
    }
    return {
        "answer": (
            "I could not retrieve evidence from every explicitly named paper, so I "
            "abstained rather than combine retrieved text with unsupported claims."
        ),
        "sources": [],
        "images": [],
        "question": question,
        "retrieved_context": [row["text"] for row in retrieved_context],
        "retrieved_chunks": retrieved_context,
        "cited_context_ids": [],
        "claims": [],
        "execution": agent_run.execution if agent_run else None,
        "retrieval_diagnostics": retrieval_diagnostics,
        "generation_diagnostics": diagnostics,
    }


def _citation_retry_prompt(prompt, required_context_groups, *, validation_code=None):
    groups = required_context_groups or {}
    failure = (
        f" The previous output failed validation ({validation_code})."
        if validation_code else ""
    )
    if not groups:
        message = (
            "Your previous response did not satisfy the citation schema."
            f"{failure} Regenerate the answer and cite only distinct DOC IDs present "
            "in the supplied context."
        )
    else:
        paper_requirements = "\n".join(
            f"- {label}: cite at least one of "
            f"{sorted(str(value) for value in context_ids)}"
            for label, context_ids in groups.items()
            if not label.startswith("Atomic evidence need:")
        )
        requirements = paper_requirements
        message = (
            "Your previous response did not satisfy required source/need coverage."
            f"{failure} Regenerate all atomic claims. Each claim must cite only chunks "
            "that support that exact statement. Every listed need_id must appear in at "
            "least one claim, paired with a citation from its allowed group. Do not invent "
            "or rename need IDs.\n" + requirements
        )
    return [*prompt, {"role": "system", "content": message}]


@observe(name="generate_answer", capture_input=False, capture_output=False)
def generate_answer(prompt, generation_model=None, allowed_context_ids=None,
                    required_context_groups=None):
    """
    Unified generation for OpenAI & Groq.

    Args:
        prompt: list of chat messages [{"role": "system", "content": "..."}]
        generation_model: explicit model name (falls back to config.GENERATION_MODEL)
    """
    generation_model = generation_model or config.GENERATION_MODEL
    logger.info(f"Using model: {generation_model}")

    logger.info("-----")
    logger.info(f"Prompt length: {len(str(prompt))}")
    logger.info(f"Prompt: {prompt}")
    logger.info("-----")

    if is_openai_model(generation_model):
        # --------- OpenAI branch ----------
        client = openai_client()
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
                 "attempts": 0}
        request_prompt = prompt
        validation_failures = []
        for attempt in range(2):
            response_json = client.chat.completions.create(
                model=generation_model,
                messages=request_prompt,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "RAGGenerationResponse",
                        "strict": True,
                        "schema": OUTPUT_SCHEMA,
                    }
                }
            )
            usage["attempts"] += 1
            if response_json.usage is not None:
                usage["input_tokens"] += response_json.usage.prompt_tokens
                usage["output_tokens"] += response_json.usage.completion_tokens
                usage["total_tokens"] += response_json.usage.total_tokens
            try:
                response = RAGGenerationResponse.model_validate_json(
                    response_json.choices[0].message.content
                )
                _validate_context_ids(
                    response, allowed_context_ids, required_context_groups,
                )
                break
            except (ValidationError, InvalidCitationIdsError, MissingRequiredCitationError) as error:
                validation_failures.append({
                    "code": getattr(error, "code", "invalid_structured_response"),
                    "exception_type": type(error).__name__,
                })
                if attempt == 1:
                    try:
                        error.validation_failures = validation_failures
                    except (AttributeError, TypeError):
                        pass
                    raise
                logger.warning("Retrying one invalid or citation-incomplete RAG response")
                request_prompt = _citation_retry_prompt(
                    prompt, required_context_groups,
                    validation_code=validation_failures[-1]["code"],
                )

    else:
        # --------- Groq branch ----------
        with observation(name="groq_generation", as_type="generation",
                         model=generation_model, input=prompt) as generation:
            groq_client = Groq(api_key=config.GROQ_API_KEY)
            instr_client = instructor.from_groq(groq_client, mode=instructor.Mode.JSON)
            usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
                     "attempts": 0}
            request_prompt = prompt
            validation_failures = []
            for attempt in range(2):
                response, raw_response = instr_client.chat.completions.create_with_completion(
                    model=generation_model,
                    response_model=RAGGenerationResponse,
                    messages=request_prompt,
                    temperature=0,
                    max_tokens=config.GENERATION_MODEL_MAX_TOKENS,
                    max_retries=5,
                )
                usage["attempts"] += 1
                usage["input_tokens"] += raw_response.usage.prompt_tokens
                usage["output_tokens"] += raw_response.usage.completion_tokens
                usage["total_tokens"] += raw_response.usage.total_tokens
                try:
                    _validate_context_ids(
                        response, allowed_context_ids, required_context_groups,
                    )
                    break
                except (InvalidCitationIdsError, MissingRequiredCitationError) as error:
                    validation_failures.append({
                        "code": getattr(error, "code", "invalid_citation"),
                        "exception_type": type(error).__name__,
                    })
                    if attempt == 1:
                        try:
                            error.validation_failures = validation_failures
                        except (AttributeError, TypeError):
                            pass
                        raise
                    logger.warning("Retrying one citation-incomplete Groq RAG response")
                    request_prompt = _citation_retry_prompt(
                        prompt, required_context_groups,
                        validation_code=validation_failures[-1]["code"],
                    )
            if generation is not None:
                generation.update(output=response.model_dump(), usage_details=usage)

    update_span(input={"messages": prompt}, output=response.model_dump(),
                metadata={"provider": "openai" if is_openai_model(generation_model) else "groq",
                          "model": generation_model, "usage": usage})

    return response



def _agentic_structured_request(messages, response_model, stage, generation_model=None):
    """One bounded provider request; Agentic answering owns the single repair."""
    model = generation_model or config.GENERATION_MODEL
    with observation(name=f"agentic_{stage}", as_type="generation",
                     model=model, input=messages) as span:
        if is_openai_model(model):
            client = openai_client().with_options(timeout=60, max_retries=0)
            verifier = stage == "verify"
            reasoning_model = str(model).casefold().startswith(("gpt-5", "o1", "o3", "o4"))
            completion_limit = (
                config.AGENT_VERIFIER_MAX_COMPLETION_TOKENS if verifier
                else config.GENERATION_MODEL_MAX_TOKENS
            )
            request_options = {
                "model": model,
                "messages": messages,
                "max_completion_tokens": completion_limit,
                "response_format": {"type": "json_schema", "json_schema": {
                    "name": response_model.__name__, "strict": True,
                    "schema": response_model.model_json_schema(),
                }},
            }
            if verifier and reasoning_model and config.AGENT_VERIFIER_REASONING_EFFORT not in ("", "none"):
                request_options["reasoning_effort"] = config.AGENT_VERIFIER_REASONING_EFFORT
            raw = client.chat.completions.create(
                **request_options,
            )
            choice = raw.choices[0]
            message = choice.message
            content = message.content or ""
            try:
                result = response_model.model_validate_json(content)
            except ValidationError as error:
                issues = error.errors(include_input=False)
                safe_diagnostics = {
                    "validation_error_codes": sorted({
                        str(issue.get("type", "invalid")) for issue in issues
                    })[:10],
                    "validation_error_locations": sorted({
                        ".".join(str(part) for part in issue.get("loc", ()))[:128]
                        for issue in issues
                    })[:10],
                    "provider_finish_reason": str(choice.finish_reason or "unknown")[:32],
                    "provider_completion_tokens": getattr(raw.usage, "completion_tokens", None),
                    "provider_content_chars": len(content),
                    "provider_refusal": bool(getattr(message, "refusal", None)),
                }
                if span is not None:
                    usage = raw.usage
                    span.update(
                        output={"structured_output_valid": False,
                                "finish_reason": safe_diagnostics["provider_finish_reason"],
                                "refusal": safe_diagnostics["provider_refusal"]},
                        usage_details={
                            "input_tokens": getattr(usage, "prompt_tokens", 0),
                            "output_tokens": getattr(usage, "completion_tokens", 0),
                            "total_tokens": getattr(usage, "total_tokens", 0),
                        },
                    )
                raise AgenticStructuredOutputError(safe_diagnostics) from error
        else:
            client = instructor.from_groq(
                Groq(api_key=config.GROQ_API_KEY, timeout=60, max_retries=0),
                mode=instructor.Mode.JSON,
            )
            result, raw = client.chat.completions.create_with_completion(
                model=model, messages=messages, response_model=response_model,
                temperature=0, max_tokens=(
                    config.AGENT_VERIFIER_MAX_COMPLETION_TOKENS
                    if stage == "verify" else config.GENERATION_MODEL_MAX_TOKENS
                ),
                max_retries=0,
            )
        if span is not None:
            usage = raw.usage
            span.update(output=result.model_dump(), usage_details={
                "input_tokens": getattr(usage, "prompt_tokens", 0),
                "output_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            })
        return result

def _claim_citations(response: RAGGenerationResponse) -> list[dict]:
    """Serialize claim provenance for the API, UI and offline evaluator."""
    return [{
        "text": claim.text,
        "cited_context_ids": list(dict.fromkeys(claim.cited_context_ids)),
        "need_ids": list(dict.fromkeys(claim.need_ids)),
    } for claim in response.claims]


def _citation_source_key(row: dict) -> tuple:
    page = row.get("page")
    page_key = tuple(sorted(str(value) for value in page)) if isinstance(page, list) else str(page or "")
    return (
        str(row.get("paper_id") or ""), str(row.get("paper_version") or ""),
        str(row.get("build_id") or ""), str(row.get("collection") or ""),
        str(row.get("source_url") or ""), tuple(row.get("authors") or []),
        str(row.get("title") or ""), str(row.get("year") or ""), page_key,
    )


def _render_claims(response: RAGGenerationResponse, contexts: list[dict]) -> tuple[str, dict[str, int]]:
    """Render inline numbered references and map each point ID to its source entry."""
    context_by_id = {str(row["id"]): row for row in contexts}
    source_numbers: dict[tuple, int] = {}
    context_source_number: dict[str, int] = {}
    for context_id in response.retrieved_context_ids:
        key = _citation_source_key(context_by_id[context_id])
        source_numbers.setdefault(key, len(source_numbers) + 1)
        context_source_number[context_id] = source_numbers[key]
    rendered = []
    for claim in response.claims:
        numbers = sorted({context_source_number[value] for value in claim.cited_context_ids})
        rendered.append(f"{claim.text} " + " ".join(f"[{value}]" for value in numbers))
    return "\n\n".join(rendered), context_source_number


@observe(name="rag_pipeline", capture_input=False, capture_output=False)
def rag_pipeline(question, qdrant_client, session_id, generation_model=None, top_k=5,
                 mode=None, collection=None, scope=None, catalogue=None, agent_model=None,
                 agent_budget=None, stage_timings: dict[str, float] | None = None):
    update_span(input={"question": question}, metadata={"mode": mode or "legacy",
        "collection": collection or config.QDRANT_COLLECTION_NAME,
        "generation_model": generation_model or config.GENERATION_MODEL, "top_k": top_k})

    retrieval_started = monotonic()
    agent_run = None
    retrieval_diagnostics = None
    required_papers = []
    def timed_rerank_context(*args, **kwargs):
        started = monotonic()
        try:
            return rerank_context(*args, **kwargs)
        finally:
            if stage_timings is not None:
                stage_timings["rerank_seconds"] = round(monotonic() - started, 3)

    # Agentic retrieval owns its bounded multi-round orchestration but reuses the
    # same final answer/citation path below.
    if mode == "agentic":
        from src.api.rag.modes.agentic.contracts import AgentBudget
        from src.api.rag.modes.agentic.executor import run_agentic

        if not isinstance(scope, (RetrievalScope, FederatedRetrievalScope)):
            raise ValueError("Agentic mode requires an explicit retrieval scope")
        if catalogue is None:
            raise ValueError("Agentic mode requires the paper catalogue")
        if agent_budget is None:
            agent_budget = AgentBudget(
                max_rounds=config.AGENT_MAX_ROUNDS,
                max_tool_calls=config.AGENT_MAX_TOOL_CALLS,
                max_parallel_tools=config.AGENT_MAX_PARALLEL_TOOLS,
                max_evidence_chunks=config.AGENT_MAX_EVIDENCE_CHUNKS,
                max_elapsed_seconds=config.AGENT_MAX_ELAPSED_SECONDS,
                max_planner_tokens=config.AGENT_MAX_PLANNER_TOKENS,
            )
        agent_run = run_agentic(
            question,
            client=qdrant_client,
            catalogue=catalogue,
            scope=scope,
            model=agent_model,
            embed=get_embedding,
            budget=agent_budget,
        )
        retrieved_context = [row.model_dump() for row in agent_run.evidence]
        if not agent_run.should_synthesize:
            if stage_timings is not None:
                stage_timings["retrieval_seconds"] = round(monotonic() - retrieval_started, 3)
            stop_reason = agent_run.execution.stop_reason.value
            if stop_reason == "planner_failure":
                answer_text = "The Agentic model could not select a valid retrieval action."
            elif stop_reason == "tool_failure":
                answer_text = "An Agentic retrieval tool failed, so the request stopped safely."
            else:
                answer_text = (
                    "I could not find sufficient indexed evidence to answer this question "
                    "within the Agentic retrieval limits."
                )
            result = {
                "answer": answer_text,
                "sources": [],
                "images": [],
                "question": question,
                "retrieved_context": [row["text"] for row in retrieved_context],
                "retrieved_chunks": retrieved_context,
                "cited_context_ids": [],
                "claims": [],
                "execution": agent_run.execution,
                "retrieval_diagnostics": retrieval_diagnostics,
            }
            update_span(output={"answer": result["answer"],
                                "retrieved_ids": [row["id"] for row in retrieved_context],
                                "cited_ids": [],
                                "stop_reason": stop_reason})
            return result
    # If in evaluation mode, return a fresh memory each time
    elif mode is not None:
        from src.api.rag.dispatcher import retrieve_for_mode
        retrieved_context = retrieve_for_mode(
            mode, question, qdrant_client, top_k=top_k, collection=collection,
            scope=scope, retrieve_context=retrieve_context,
            rerank_context=timed_rerank_context,
        )
        retrieval_diagnostics = getattr(retrieved_context, "diagnostics", None)
        required_papers = _resolve_required_papers(catalogue, scope, question)
    elif os.getenv("EVALUATION_MODE") == "true":
        
        # just use hybrid retrieval without reranking
        retrieved_context = retrieve_context(question, qdrant_client, top_k=5)

    else: # normal mode: with larger hybrid retrieval + reranking
        # Initial Hybrid retrieval from Qdrant
        retrieved_context = retrieve_context(question, qdrant_client, top_k=20)  # fetch more initially, because we will rerank
        
        # Rerank with Cohere
        retrieved_context = timed_rerank_context(question, retrieved_context, top_n=top_k)

    if stage_timings is not None:
        stage_timings["retrieval_seconds"] = round(monotonic() - retrieval_started, 3)

    if not retrieved_context:
        result = {"answer": "I found no indexed evidence for this question in the selected corpus.",
                  "sources": [], "images": [], "question": question, "retrieved_context": [],
                  "retrieved_chunks": [], "cited_context_ids": [], "claims": [],
                  "execution": agent_run.execution if agent_run else None,
                  "retrieval_diagnostics": retrieval_diagnostics}
        update_span(output={"answer": result["answer"], "retrieved_ids": [], "cited_ids": []})
        return result

    missing_required_papers = _missing_required_papers(required_papers, retrieved_context)
    if missing_required_papers and agent_run is None:
        result = _coverage_abstention(
            question, retrieved_context, agent_run=agent_run,
            retrieval_diagnostics=retrieval_diagnostics,
            required_papers=required_papers,
            missing_papers=missing_required_papers,
        )
        update_span(output={
            "answer": result["answer"],
            "retrieved_ids": [row["id"] for row in retrieved_context],
            "cited_ids": [],
            "generation_diagnostics": result["generation_diagnostics"],
        })
        return result

    prompt = build_prompt(
        {
            "retrieved_context_ids": [c["id"] for c in retrieved_context],
            "retrieved_context": [f"Title: {c.get('title')}; arXiv: {c.get('arxiv_id')}; "
                                  f"version: {c.get('paper_version')}; page: {c.get('page')}\n{c['text']}"
                                  for c in retrieved_context]
        },
        question,
        session_id
    )
    generation_diagnostics = None
    answer_limitations = []

    # Baseline generation remains unchanged; Agentic has its own reviewed synthesis.
    generation_started = monotonic()
    try:
        if agent_run is not None:
            reviewed = generate_agentic_answer(
                question=question, requirements=agent_run.requirements,
                contexts=retrieved_context, prompt=prompt,
                evidence_by_requirement=agent_run.evidence_by_requirement,
                request=lambda messages, schema, stage: _agentic_structured_request(
                    messages, schema, stage,
                    config.AGENT_MODEL if stage == "verify" else generation_model),
                reviewer_model=config.AGENT_MODEL,
            )
            answer = reviewed.response
            generation_diagnostics = reviewed.diagnostics
            answer_limitations = reviewed.limitations
        else:
            answer = generate_answer(
                prompt, generation_model,
                allowed_context_ids={str(c["id"]) for c in retrieved_context},
                required_context_groups=_required_citation_groups(question, retrieved_context),
            )
    except (ValidationError, InvalidCitationIdsError, MissingRequiredCitationError) as error:
        generation_diagnostics = {
            "status": "safe_abstention",
            "reason": "citation_validation_failed",
            "exception_type": type(error).__name__,
            "attempts": 2,
        }
        validation_failures = getattr(error, "validation_failures", None)
        if validation_failures:
            generation_diagnostics["validation_failures"] = validation_failures
        result = {
            "answer": (
                "I found potentially relevant indexed evidence, but could not produce an "
                "answer with valid source citations. I abstained rather than return an "
                "unsupported answer."
            ),
            "sources": [],
            "images": [],
            "question": question,
            "retrieved_context": [row["text"] for row in retrieved_context],
            "retrieved_chunks": retrieved_context,
            "cited_context_ids": [],
            "claims": [],
            "execution": agent_run.execution if agent_run else None,
            "retrieval_diagnostics": retrieval_diagnostics,
            "generation_diagnostics": generation_diagnostics,
        }
        trace_output = {
            "answer": result["answer"],
            "retrieved_ids": [row["id"] for row in retrieved_context],
            "cited_ids": [],
            "generation_diagnostics": generation_diagnostics,
        }
        if agent_run is not None:
            trace_output["agent_execution"] = agent_run.execution.model_dump(mode="json")
        if retrieval_diagnostics is not None:
            trace_output["retrieval_diagnostics"] = retrieval_diagnostics
        update_span(output=trace_output)
        return result
    except Exception as error:
        # Preserve safe Agentic execution metadata for the benchmark failure record.
        # The original exception type/cause remains intact for diagnostics.
        if agent_run is not None:
            try:
                error.agent_execution = agent_run.execution
            except Exception:
                pass
        if retrieval_diagnostics is not None:
            try:
                error.retrieval_diagnostics = retrieval_diagnostics
            except Exception:
                pass
        raise
    finally:
        if stage_timings is not None:
            stage_timings["generation_seconds"] = round(monotonic() - generation_started, 3)

    if not answer.claims:
        generation_diagnostics = generation_diagnostics or {
            "status": "safe_abstention",
            "reason": "no_supported_claims",
            "attempts": 1,
        }
        result = {
            "answer": "I could not find sufficient indexed evidence to answer this question.",
            "sources": [],
            "images": [],
            "question": question,
            "retrieved_context": [row["text"] for row in retrieved_context],
            "retrieved_chunks": retrieved_context,
            "cited_context_ids": [],
            "claims": [],
            "execution": agent_run.execution if agent_run else None,
            "retrieval_diagnostics": retrieval_diagnostics,
            "generation_diagnostics": generation_diagnostics,
        }
        update_span(output={
            "answer": result["answer"],
            "retrieved_ids": [row["id"] for row in retrieved_context],
            "cited_ids": [],
            "generation_diagnostics": generation_diagnostics,
        })
        return result

    # Build numbered source entries in the same first-use order as inline claim citations.
    claims = _claim_citations(answer)
    rendered_answer, context_source_numbers = _render_claims(answer, retrieved_context)
    if answer_limitations:
        rendered_answer += "\n\nI could not verify these requested details from the retrieved evidence:\n" + "\n".join(
            f"- {detail}" for detail in dict.fromkeys(answer_limitations))
    used_ids = set(answer.retrieved_context_ids)
    context_by_id = {str(row["id"]): row for row in retrieved_context}
    source_rows: dict[int, list[dict]] = {}
    for context_id in answer.retrieved_context_ids:
        number = context_source_numbers[context_id]
        source_rows.setdefault(number, []).append(context_by_id[context_id])

    unique_sources = []
    for number in sorted(source_rows):
        rows = source_rows[number]
        first = rows[0]
        pages = sorted({parsed_page for row in rows
                        for raw_page in (row.get("page") if isinstance(row.get("page"), list)
                                         else [row.get("page")])
                        if (parsed_page := optional_int(raw_page)) is not None})
        unique_sources.append(Source(
            id=str(first["id"]),
            evidence_ids=[str(row["id"]) for row in rows],
            title=first.get("title"),
            authors=first.get("authors") or [],
            paper_id=first.get("paper_id"),
            arxiv_id=first.get("arxiv_id"),
            paper_version=first.get("paper_version"),
            source_url=first.get("source_url"),
            year=optional_int(first.get("year")),
            page=pages,
        ))

    logger.info("Numbered sources after claim-level citation mapping: %s", unique_sources)

    # Extract Used Images (NEW LOGIC)
    used_images = []
    for chunk in retrieved_context:
        # Check if this chunk was CITIED by the LLM and is a FIGURE
        if chunk["id"] in used_ids and chunk.get("type") == "figure":
            used_images.append({
                "url": f"/api/images/{os.path.basename(chunk['image_path'])}", # Secure local URL
                "caption": chunk.get("caption") or "Relevant Figure",
                "page": chunk.get("page"),
                "file_title": chunk.get("title")
            })

    # Extract just the text content from the retrieved_context objects
    retrieved_context_texts = [c["text"] for c in retrieved_context]

    result = {
        "answer": rendered_answer,
        "sources": unique_sources, # Text sources
        "images": used_images,     # Image sources
        "question": question,
        "retrieved_context": retrieved_context_texts,
        # Internal evaluation/observability detail. The public API wrapper below
        # deliberately does not expose full chunks or model-selected point IDs.
        "retrieved_chunks": retrieved_context,
        "cited_context_ids": sorted(used_ids.intersection(c["id"] for c in retrieved_context)),
        "claims": claims,
        "execution": agent_run.execution if agent_run else None,
        "retrieval_diagnostics": retrieval_diagnostics,
        "generation_diagnostics": generation_diagnostics,
    }
    trace_output = {"answer": result["answer"],
        "retrieved_ids": [row["id"] for row in retrieved_context],
        "cited_ids": result["cited_context_ids"],
        "claims": claims,
        "generation_diagnostics": generation_diagnostics}
    if agent_run is not None:
        trace_output["agent_execution"] = agent_run.execution.model_dump(mode="json")
    if retrieval_diagnostics is not None:
        trace_output["retrieval_diagnostics"] = retrieval_diagnostics
    update_span(output=trace_output)
    return result


def rag_pipeline_wrapper(question, session_id, generation_model=None, top_k=5,
                         mode=None, collection=None, scope=None):
    
    qdrant_client = QdrantClient(
        url=config.QDRANT_URL, # QDRANT_URL=http://qdrant:6333 when local, or web URL for Qdrant Cloud
        port=config.qdrant_port,
        api_key=config.QDRANT_API_KEY  # For Qdrant Cloud only, empty otherwise
    )
        
    catalogue = None
    try:
        if mode in {"vanilla", "hybrid", "hybrid_rerank", "agentic"}:
            from src.api.papers.catalogue import Catalogue
            from src.api.papers.settings import PaperSettings

            catalogue = Catalogue(PaperSettings().PAPERS_DATABASE_URL)
            catalogue.require_schema()
        with trace_attributes(session_id=session_id,
                tags=["rag", f"mode:{mode or 'legacy'}"],
                metadata={"mode": mode or "legacy", "collection": collection or config.QDRANT_COLLECTION_NAME}):
            result = rag_pipeline(question, qdrant_client, session_id, generation_model, top_k,
                                  mode=mode, collection=collection, scope=scope,
                                  catalogue=catalogue)
    finally:
        if catalogue is not None:
            catalogue.close()
        qdrant_client.close()

    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "images": result.get("images", []),
        "execution": result.get("execution"),
        "claims": result.get("claims", []),
        "generation_diagnostics": result.get("generation_diagnostics"),
    }
