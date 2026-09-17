# src/api/rag/retrieval.py
import os
import instructor
from groq import Groq
from pydantic import BaseModel, ConfigDict, ValidationError
import json
import cohere
from qdrant_client import QdrantClient
import logging
import redis
import pickle

from src.api.core.config import config
from src.api.core.clients import openai_client
from src.api.observability.tracing import observe, observation, trace_attributes, update_span
from src.api.rag.utils.utils import prompt_template_config
from src.api.rag.summarize import summarize_text
from src.api.api.models import Source
from src.api.rag.search import search_points
from src.api.rag.contracts import RetrievalScope
from src.api.rag.tools.chunk_search import search_chunks


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
    query_embedding = get_embedding(query)

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


@observe(name="rerank_context", as_type="reranker", capture_input=False, capture_output=False)
def rerank_context(query: str, retrieved_context: list, top_n: int = 5):
    """
    Reranks the retrieved context chunks using Cohere's reranker.
    """

    if not retrieved_context:
        return []
    docs = [c["text"] for c in retrieved_context]

    response = cohere_client.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=docs,
        top_n=top_n
    )

    # Map reranked results back to original retrieved_context items
    reranked = []
    for r in response.results:
        doc_idx = r.index
        doc_score = r.relevance_score
        chunk = retrieved_context[doc_idx]
        reranked.append({
            **chunk,
            "rerank_score": doc_score
        })

    update_span(input={"query": query, "candidate_ids": [row["id"] for row in retrieved_context]},
                output={"point_ids": [row["id"] for row in reranked]},
                metadata={"model": "rerank-english-v3.0", "top_n": top_n})
    return reranked


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


class RAGGenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    retrieved_context_ids: list[str]


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


def _validate_context_ids(response, allowed_context_ids):
    if allowed_context_ids is None:
        return response
    allowed = {str(value) for value in allowed_context_ids}
    selected = response.retrieved_context_ids
    if len(selected) != len(set(selected)) or not set(selected).issubset(allowed):
        raise InvalidCitationIdsError
    return response


@observe(name="generate_answer", capture_input=False, capture_output=False)
def generate_answer(prompt, generation_model=None, allowed_context_ids=None):
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
        for attempt in range(2):
            response_json = client.chat.completions.create(
                model=generation_model,
                messages=prompt,
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
                _validate_context_ids(response, allowed_context_ids)
                break
            except (ValidationError, InvalidCitationIdsError):
                if attempt == 1:
                    raise
                logger.warning("Retrying one malformed structured RAG response")

    else:
        # --------- Groq branch ----------
        with observation(name="groq_generation", as_type="generation",
                         model=generation_model, input=prompt) as generation:
            groq_client = Groq(api_key=config.GROQ_API_KEY)
            instr_client = instructor.from_groq(groq_client, mode=instructor.Mode.JSON)
            response, raw_response = instr_client.chat.completions.create_with_completion(
                model=generation_model,
                response_model=RAGGenerationResponse,
                messages=prompt,
                temperature=0,
                max_tokens=config.GENERATION_MODEL_MAX_TOKENS,
                max_retries=5,
            )
            _validate_context_ids(response, allowed_context_ids)
            usage = {
                "input_tokens": raw_response.usage.prompt_tokens,
                "output_tokens": raw_response.usage.completion_tokens,
                "total_tokens": raw_response.usage.total_tokens,
            }
            if generation is not None:
                generation.update(output=response.model_dump(), usage_details=usage)

    update_span(input={"messages": prompt}, output=response.model_dump(),
                metadata={"provider": "openai" if is_openai_model(generation_model) else "groq",
                          "model": generation_model, "usage": usage})

    return response


@observe(name="rag_pipeline", capture_input=False, capture_output=False)
def rag_pipeline(question, qdrant_client, session_id, generation_model=None, top_k=5,
                 mode=None, collection=None, scope=None, catalogue=None, planner=None,
                 agent_budget=None):
    update_span(input={"question": question}, metadata={"mode": mode or "legacy",
        "collection": collection or config.QDRANT_COLLECTION_NAME,
        "generation_model": generation_model or config.GENERATION_MODEL, "top_k": top_k})

    agent_run = None
    # Agentic retrieval owns its bounded multi-round orchestration but reuses the
    # same final answer/citation path below.
    if mode == "agentic":
        from src.api.rag.modes.agentic.contracts import AgentBudget
        from src.api.rag.modes.agentic.executor import run_agentic
        from src.api.rag.modes.agentic.planner import OpenAIAgentPlanner

        if not isinstance(scope, RetrievalScope):
            raise ValueError("Agentic mode requires an explicit retrieval scope")
        if catalogue is None:
            raise ValueError("Agentic mode requires the paper catalogue")
        if agent_budget is None:
            agent_budget = AgentBudget(
                max_rounds=config.AGENT_MAX_ROUNDS,
                max_tool_calls=config.AGENT_MAX_TOOL_CALLS,
                max_evidence_chunks=config.AGENT_MAX_EVIDENCE_CHUNKS,
                max_elapsed_seconds=config.AGENT_MAX_ELAPSED_SECONDS,
                max_planner_tokens=config.AGENT_MAX_PLANNER_TOKENS,
            )
        agent_run = run_agentic(
            question,
            client=qdrant_client,
            catalogue=catalogue,
            scope=scope,
            planner=planner or OpenAIAgentPlanner(),
            embed=get_embedding,
            budget=agent_budget,
        )
        retrieved_context = [row.model_dump() for row in agent_run.evidence]
        if not agent_run.should_synthesize:
            failure_reasons = {"planner_failure", "tool_failure"}
            if agent_run.execution.stop_reason.value in failure_reasons:
                answer_text = "Agentic retrieval could not complete safely for this question."
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
                "execution": agent_run.execution,
            }
            update_span(output={"answer": result["answer"],
                                "retrieved_ids": [row["id"] for row in retrieved_context],
                                "cited_ids": [],
                                "stop_reason": agent_run.execution.stop_reason.value})
            return result
    # If in evaluation mode, return a fresh memory each time
    elif mode is not None:
        from src.api.rag.dispatcher import retrieve_for_mode
        retrieved_context = retrieve_for_mode(
            mode, question, qdrant_client, top_k=top_k, collection=collection,
            scope=scope, retrieve_context=retrieve_context,
            rerank_context=rerank_context,
        )
    elif os.getenv("EVALUATION_MODE") == "true":
        
        # just use hybrid retrieval without reranking
        retrieved_context = retrieve_context(question, qdrant_client, top_k=5)

    else: # normal mode: with larger hybrid retrieval + reranking
        # Initial Hybrid retrieval from Qdrant
        retrieved_context = retrieve_context(question, qdrant_client, top_k=20)  # fetch more initially, because we will rerank
        
        # Rerank with Cohere
        retrieved_context = rerank_context(question, retrieved_context, top_n=top_k)

    if not retrieved_context:
        result = {"answer": "I found no indexed evidence for this question in the selected corpus.",
                  "sources": [], "images": [], "question": question, "retrieved_context": [],
                  "retrieved_chunks": [], "cited_context_ids": [],
                  "execution": agent_run.execution if agent_run else None}
        update_span(output={"answer": result["answer"], "retrieved_ids": [], "cited_ids": []})
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

    # Generate answer using LLM
    answer = generate_answer(prompt, generation_model,
                             allowed_context_ids={str(c["id"]) for c in retrieved_context})

    # Deduplicate sources and aggregate page numbers
    seen = {}
    unique_sources = []

    used_ids = set(answer.retrieved_context_ids)
    for c in retrieved_context:
        if str(c["id"]) not in used_ids:
            continue
        key = (c.get("paper_id"), c.get("paper_version"), tuple(c.get("authors") or []), c.get("title"), c.get("year"))
        page_num = c.get("page")

        # Ensure page_num is always an integer if present
        if page_num is not None:
            if isinstance(page_num, list):
                page_num = [int(p) for p in page_num]
            else:
                page_num = [int(page_num)]
        else:
            page_num = []

        if key not in seen:
            s = Source(
                id=str(c["id"]),
                title=c.get("title"),
                authors=c.get("authors") or [],
                paper_id=c.get("paper_id"),
                arxiv_id=c.get("arxiv_id"),
                paper_version=c.get("paper_version"),
                source_url=c.get("source_url"),
                year=optional_int(c.get("year")),
                page=page_num
            )
            seen[key] = s
            unique_sources.append(s)
        else:
            # Aggregate page numbers for duplicate sources
            # if page_num is not None and page_num not in seen[key].page:
            #     seen[key].page.append(page_num)
            existing_pages = set(seen[key].page)
            existing_pages.update(page_num)
            seen[key].page = sorted(existing_pages)            

    # Only cited chunks were grouped, so uncited pages cannot enter these sources.
    logger.info(f"Unique sources after filtering: {unique_sources}")

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
        "answer": answer.answer,
        "sources": unique_sources, # Text sources
        "images": used_images,     # Image sources
        "question": question,
        "retrieved_context": retrieved_context_texts,
        # Internal evaluation/observability detail. The public API wrapper below
        # deliberately does not expose full chunks or model-selected point IDs.
        "retrieved_chunks": retrieved_context,
        "cited_context_ids": sorted(used_ids.intersection(c["id"] for c in retrieved_context)),
        "execution": agent_run.execution if agent_run else None,
    }
    update_span(output={"answer": result["answer"],
        "retrieved_ids": [row["id"] for row in retrieved_context],
        "cited_ids": result["cited_context_ids"]})
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
        if mode == "agentic":
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
    }
