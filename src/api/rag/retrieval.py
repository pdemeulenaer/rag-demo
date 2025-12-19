# src/api/rag/retrieval.py
import os
import openai
import instructor
from openai import OpenAI
from groq import Groq
from pydantic import BaseModel
from typing import List
import json
import cohere
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, Filter, FieldCondition, MatchText, FusionQuery
from langsmith import traceable, get_current_run_tree
import logging
import redis
import pickle

from src.api.core.config import config
from src.api.rag.utils.utils import prompt_template_config, prompt_template_registry
from src.api.rag.summarize import summarize_text
from src.api.api.models import Source


logger = logging.getLogger(__name__)
cohere_client = cohere.Client(config.COHERE_API_KEY)

# Initialize the conversation memory
redis_client = redis.Redis(host='redis', port=6379, db=0)


def titles_by_author(author, year=None):
    if not author:
        return []

class ConversationMemory:
    def __init__(self, window_size=10): # 10 messages, i.e. 5 question-answer turns
        self.recent_messages = []
        self.full_history = [] 
        self.summary = ""
        self.window_size = window_size


@traceable(
    name="summarize_conversation",
    run_type="prompt",
)
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


@traceable(
    name="get_memory",
    # run_type="prompt",
)
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


@traceable(
    name="add_message",
    # run_type="prompt",
)
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


@traceable(
    name="embed_query",
    run_type="embedding",
    metadata={"ls_provider": config.EMBEDDING_MODEL_PROVIDER, "ls_model_name": config.EMBEDDING_MODEL}
)
def get_embedding(text, model=config.EMBEDDING_MODEL):
    response = openai.embeddings.create(
        input=[text],
        model=model,
    )

    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return response.data[0].embedding


@traceable(
    name="retrieve_top_n",
    run_type="retriever"
)
def retrieve_context(query, qdrant_client, top_k=5):
    query_embedding = get_embedding(query)

    # # SIMPLE SEARCH
    # results = qdrant_client.query_points(
    #     collection_name=config.QDRANT_COLLECTION_NAME,
    #     query=query_embedding,
    #     limit=5,
    # )    

    # HYBRID SEARCH
    results = qdrant_client.query_points(
        collection_name=config.QDRANT_COLLECTION_NAME,
        prefetch=[
            Prefetch(
                query=query_embedding,
                limit=20
            ),
            Prefetch(
                filter=Filter(
                    must=[
                        # still search the main chunk text
                        FieldCondition(key="text", match=MatchText(text=query)),
                        # add metadata fields you’d like to search
                        # FieldCondition(key="authors", match=MatchText(text=query)),
                        # FieldCondition(key="file_title", match=MatchText(text=query)),
                        # FieldCondition(key="year", match=MatchText(text=query)),
                        # FieldCondition(key="keywords", match=MatchText(text=query)),                                                                 
                    ]
                    
                ),
                limit=20
            )
        ],
        query=FusionQuery(fusion="rrf"),
        limit=top_k
    )

    retrieved_context = []
    for result in results.points:
        logger.info("Qdrant payload keys: %s", result.payload.keys())
        # logger.info("Qdrant payload sample: %s", result.payload)     
        # retrieved_context.append({
        #     "id": result.id,
        #     "text": result.payload["text"],
        #     "title": result.payload.get("file_title"),
        #     "authors": result.payload.get("authors"),
        #     "year": result.payload.get("year"),
        #     "page": result.payload.get("page_number"),
        #     "score": result.score            
        # })

        # payload is a dict, so we can use .get() safely
        payload = result.payload
        
        retrieved_context.append({
            "id": str(result.id),
            "text": payload["text"],
            "title": payload.get("file_title"),
            "authors": payload.get("authors"),
            "year": payload.get("year"),
            "page": payload.get("page_number"),
            "score": result.score,
            # --- NEW FIELDS PRESERVED ---
            "type": payload.get("type", "text"),  # 'text' or 'figure'
            "image_path": payload.get("image_path"), # Only present if type='figure'
            "caption": payload.get("caption")        # Important for UI display
        })        

    return retrieved_context    


@traceable(
    name="rerank_context",
    run_type="reranker",
    metadata={"ls_provider": "Cohere", "ls_model_name": "rerank-english-v3.0"}
)
def rerank_context(query: str, retrieved_context: list, top_n: int = 5):
    """
    Reranks the retrieved context chunks using Cohere's reranker.
    """

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

    return reranked


@traceable(
    name="format_retrieved_context",
    run_type="prompt"
)
def process_context(context):
    lines = []
    for id, chunk in zip(context["retrieved_context_ids"], context["retrieved_context"]):
        lines.append(f"\n\n DOC ID: {id}; DOC TEXT: {chunk}\n\n---")
    return "\n".join(lines)


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "retrieved_context_ids": {
            "type": "array",
            "items": {"type": "string"}
        },
        "used_chunks_rationale": {"type": "string"} # NEW 2025-11-15: field explaining why certain chunks were used
    },
    "required": ["answer", "retrieved_context_ids"]
}


# @traceable(
#     name="render_prompt",
#     run_type="prompt"
# )
def build_prompt(context, question, session_id):
    memory = get_memory(session_id)

    formatted_recent = "\n".join(
        [f"{msg['role'].capitalize()}: {msg['content']}" for msg in memory.recent_messages]
    )

    full_history = f"Conversation Summary:\n{memory.summary.strip()}\n\nRecent Messages:\n{formatted_recent}"

    processed_context = process_context(context)

    # Extract the prompt template
    # prompt_template = prompt_template_registry("rag-prompt")
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

    # For LangSmith trace: return a string instead of the messages list
    traced_prompt = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"

    @traceable(name="render_prompt", run_type="prompt")
    def traced():
        return traced_prompt

    traced()  # just logs the prompt

    # Return messages for actual LLM call
    return messages


class RAGUsedContext(BaseModel):
    id: str #int # changed from Aurimas' code since here we use uuid as strings
    description: str

class RAGGenerationResponse(BaseModel):
    answer: str
    # retrieved_context_ids: List[RAGUsedContext]
    retrieved_context_ids: List[str]  # changed from Aurimas' code since we don't need description here

class RAGSummarizationResponse(BaseModel):
    summary: str    


def is_openai_model(model_name: str) -> bool:
    """
    Decide provider by simple naming convention.
    Adjust if you add custom prefixes.
    """
    model_name = model_name.lower()
    return model_name.startswith("gpt-") or model_name.startswith("o1-") or model_name.startswith("openai-")


@traceable(
    name="generate_answer",
    run_type="llm",
    metadata={"ls_provider": config.GENERATION_MODEL_PROVIDER, "ls_model_name": config.GENERATION_MODEL}
)
# def generate_answer(prompt: List[Dict[str, str]], generation_model: str = None):
def generate_answer(prompt, generation_model=None):
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
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response_json = client.chat.completions.create(
            model=generation_model,
            messages=prompt,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "RAGGenerationResponse",
                    "schema": OUTPUT_SCHEMA
                }
            }
        )

        raw_content = response_json.choices[0].message.content
        parsed_content = json.loads(raw_content)
        response = RAGGenerationResponse(**parsed_content)

        usage = {
            "input_tokens": response_json.usage.prompt_tokens,
            "output_tokens": response_json.usage.completion_tokens,
            "total_tokens": response_json.usage.total_tokens,
        }

    else:
        # --------- Groq branch ----------
        groq_client = Groq(api_key=config.GROQ_API_KEY)
        instr_client = instructor.from_groq(groq_client)

        response, raw_response = instr_client.chat.completions.create_with_completion(
            model=generation_model,
            response_model=RAGGenerationResponse,
            messages=prompt,
            temperature=0,
            max_tokens=config.GENERATION_MODEL_MAX_TOKENS,
            max_retries=5,
        )

        usage = {
            "input_tokens": raw_response.usage.prompt_tokens,
            "output_tokens": raw_response.usage.completion_tokens,
            "total_tokens": raw_response.usage.total_tokens,
        }

    # attach token usage to LangSmith run if present
    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = usage

    return response


@traceable(
    name="rag_pipeline",
    run_type="chain"
)
def rag_pipeline(question, qdrant_client, session_id, generation_model=None, top_k=5):

    # If in evaluation mode, return a fresh memory each time
    if os.getenv("EVALUATION_MODE") == "true":
        
        # just use hybrid retrieval without reranking
        retrieved_context = retrieve_context(question, qdrant_client, top_k=5)

    else: # normal mode: with larger hybrid retrieval + reranking
        # Initial Hybrid retrieval from Qdrant
        retrieved_context = retrieve_context(question, qdrant_client, top_k=20)  # fetch more initially, because we will rerank
        
        # Rerank with Cohere
        retrieved_context = rerank_context(question, retrieved_context, top_n=top_k)

    prompt = build_prompt(
        {
            "retrieved_context_ids": [c["id"] for c in retrieved_context],
            "retrieved_context": [c["text"] for c in retrieved_context]
        },
        question,
        session_id
    )

    # Generate answer using LLM
    answer = generate_answer(prompt, generation_model)

    # Deduplicate sources and aggregate page numbers
    seen = {}
    unique_sources = []

    for c in retrieved_context:
        key = (tuple(c.get("authors", [])), c.get("title"), c.get("year"))
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
                authors=c.get("authors", []),
                year=c.get("year"),
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

    # Filter out unused sources based on retrieved_context_ids
    used_ids = set(answer.retrieved_context_ids)
    unique_sources = [s for s in unique_sources if s.id in used_ids]
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

    return {
        "answer": answer.answer,
        "sources": unique_sources, # Text sources
        "images": used_images,     # Image sources
        "question": question,
        "retrieved_context": retrieved_context_texts,
    }


def rag_pipeline_wrapper(question, session_id, generation_model=None, top_k=5):
    
    qdrant_client = QdrantClient(
        url=config.QDRANT_URL, # QDRANT_URL=http://qdrant:6333 when local, or web URL for Qdrant Cloud
        api_key=config.QDRANT_API_KEY  # For Qdrant Cloud only, empty otherwise
    )
        
    result = rag_pipeline(question, qdrant_client, session_id, generation_model, top_k)

    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
    }