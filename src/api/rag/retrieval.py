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
from src.api.api.models import Source


logger = logging.getLogger(__name__)
cohere_client = cohere.Client(config.COHERE_API_KEY)

# Initialize the conversation memory
# conversation_memory = {} # global memory dictionary, deprecated in favor of Redis
redis_client = redis.Redis(host='redis', port=6379, db=0)




class ConversationMemory:
    def __init__(self, window_size=10): # 10 messages, i.e. 5 question-answer turns
        self.recent_messages = []
        self.full_history = [] 
        self.summary = ""
        self.window_size = window_size


@traceable(
    name="summarize_messages",
    run_type="prompt",
)
def summarize_messages(messages, summarizer_llm):
    """
    Summarizes the conversation history using the given LLM client (Groq in this case).
    This version works without Instructor's create_with_completion.
    """
    # Convert messages list to a readable string
    formatted_messages = "\n".join(
        [f"{m['role'].capitalize()}: {m['content']}" for m in messages]
    )

    prompt = f"""
    Please summarize the following conversation briefly, preserving key facts, names, and context
    so that future turns can be understood without losing important details.
    
    Conversation:
    {formatted_messages}
    """

    response = summarizer_llm.chat.completions.create(
        model=config.SUMMARIZATION_MODEL, # "llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=config.SUMMARIZATION_MODEL_TEMPERATURE, # 0.5,
        response_model=RAGSummarizationResponse,
        max_tokens=config.SUMMARIZATION_MODEL_MAX_TOKENS # 1000
    )

    # return response.choices[0].message.content.strip()
    return response.summary.strip()


@traceable(
    name="get_memory",
    # run_type="prompt",
)
# def get_memory(session_id: str) -> ConversationMemory:
#     # global conversation_memory, based on session_id
#     if session_id not in conversation_memory:
#         conversation_memory[session_id] = ConversationMemory()
#     return conversation_memory[session_id]
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
def add_message(session_id: str, role: str, content: str, summarizer_llm):
    memory = get_memory(session_id)

    # Add message to both lists
    memory.recent_messages.append({"role": role, "content": content})
    memory.full_history.append({"role": role, "content": content})


    # Summarize older messages if buffer exceeded
    if len(memory.recent_messages) > memory.window_size:
        # Get messages to summarize (all but the most recent)
        old_messages = memory.recent_messages[:-memory.window_size]
        summary_update = summarize_messages(old_messages, summarizer_llm)
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
                        FieldCondition(
                            key="text",
                            match=MatchText(text=query)
                        )
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
        # print("Qdrant payload keys:", result.payload.keys())
        # print("Qdrant payload sample:", result.payload)
        logger.info("Qdrant payload keys: %s", result.payload.keys())
        logger.info("Qdrant payload sample: %s", result.payload)     
        retrieved_context.append({
            "id": result.id,
            "text": result.payload["text"],
            "title": result.payload.get("file_title"),
            "authors": result.payload.get("authors"),
            "year": result.payload.get("year"),
            "page": result.payload.get("page_number"),
            "score": result.score            
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
# def process_context(context):

#     formatted_context = ""

#     for id, chunk in zip(context["retrieved_context_ids"], context["retrieved_context"]):
#         formatted_context += f"- {id}: {chunk}\n"

#     return formatted_context
def process_context(context):
    lines = []
    for id, chunk in zip(context["retrieved_context_ids"], context["retrieved_context"]):
        lines.append(f"\n\n DOC ID: {id}; DOC TEXT: {chunk}\n\n---")
    return "\n".join(lines)


# OUTPUT_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "answer": {
#             "type": "string",
#             "description": "The answer to the question based on the provided context.",
#         },
#         "retrieved_context_ids": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "id": {
#                         "type": "string", #"integer",
#                         "description": "The uuid index of the chunk that was used to answer the question.",
#                     },
#                     "description": {
#                         "type": "string",
#                         "description": "Short description of the item based on the context together with the id.",
#                     },
#                 },
#             },
#         },
#     },
# }

# OUTPUT_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "answer": {
#             "type": "string",
#             "description": "The answer to the question based on the provided documentation."
#         },
#         "retrieved_context_ids": {
#             "type": "array",
#             "items": {
#                 "type": "string",
#                 "description": "UUID of a document chunk that was used to answer the question."
#             }
#         },
#     },
#     "required": ["answer", "retrieved_context_ids"]
# }

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "retrieved_context_ids": {
            "type": "array",
            "items": {"type": "string"}
        }
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

    full_history = f"Conversation Summary:\n{memory.summary}\n\nRecent Messages:\n{formatted_recent}"

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

    # # Instructor trace can log the string
    # from langsmith import traceable

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


@traceable(
    name="generate_answer",
    run_type="llm",
    metadata={"ls_provider": config.GENERATION_MODEL_PROVIDER, "ls_model_name": config.GENERATION_MODEL}
)
def generate_answer(prompt, generation_model=None):

    # client = instructor.from_openai(OpenAI(api_key=config.OPENAI_API_KEY))
    # response, raw_response = client.chat.completions.create_with_completion(
    #     model="gpt-4.1", #"gpt-5-mini", # "gpt-4.1", #
    #     response_model=RAGGenerationResponse,
    #     messages=[{"role": "user", "content": prompt}],
    #     temperature=0.5,
    # )

    # Call OpenAI with JSON output enforcement
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response_json = client.chat.completions.create(
        model=generation_model, #config.GENERATION_MODEL, # "gpt-4.1",
        # messages=[
        #     {"role": "system", "content": "You are a helpful assistant."},
        #     {"role": "user", "content": "Answer using JSON format."}
        # ],
        messages=prompt,
        # temperature=0,
        # max_tokens=1024,
        # response_format={"type": "json_schema", "json_schema": OUTPUT_SCHEMA}
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "RAGGenerationResponse",
                "schema": OUTPUT_SCHEMA
            }
        }
    )

    raw_content = response_json.choices[0].message.content
    parsed_content = json.loads(raw_content)  # now it's a dict

    # Parse the JSON into your Pydantic model
    response = RAGGenerationResponse(**parsed_content)    

    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": response_json.usage.prompt_tokens,
            "output_tokens": response_json.usage.completion_tokens,
            "total_tokens": response_json.usage.total_tokens,
        }

    return response


@traceable(
    name="generate_answer",
    run_type="llm",
    metadata={"ls_provider": config.GENERATION_MODEL_PROVIDER, "ls_model_name": config.GENERATION_MODEL}
)
def generate_answer_groq(prompt, generation_model=None):    

    # Initialize the Groq client
    groq_client = Groq(api_key=config.GROQ_API_KEY)

    # Patch the Groq client with instructor
    client = instructor.from_groq(groq_client)

    logger.info(f"-----")
    logger.info(f"Prompt length: {len(prompt)}")
    logger.info(f"Prompt: {prompt}")
    logger.info(f"-----")

    # Use the instructor-patched Groq client for chat completions
    response, raw_response = client.chat.completions.create_with_completion(
        model=generation_model, # config.GENERATION_MODEL, # "llama-3.3-70b-versatile",
        response_model=RAGGenerationResponse,
        messages=prompt, #[{"role": "user", "content": prompt}],
        temperature=0, #config.GENERATION_MODEL_TEMPERATURE, #0.5,
        max_tokens=config.GENERATION_MODEL_MAX_TOKENS, #1024
        max_retries=5,  # Set the number of retries here
    )

    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": raw_response.usage.prompt_tokens,
            "output_tokens": raw_response.usage.completion_tokens,
            "total_tokens": raw_response.usage.total_tokens,
        }

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
    answer = generate_answer(prompt, generation_model) # openai's one
    # answer = generate_answer_groq(prompt, generation_model)

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
            # Aggregate page numbers for duplicate sources
            existing_pages = set(seen[key].page)
            existing_pages.update(page_num)
            seen[key].page = sorted(existing_pages)            

    # Extract just the text content from the retrieved_context objects
    retrieved_context_texts = [c["text"] for c in retrieved_context]

    return {
        "answer": answer.answer,
        "sources": unique_sources, # [s.__dict__ for s in unique_sources], # make sources JSON serializable #
        "question": question,
        "retrieved_context": retrieved_context_texts,
    }



def rag_pipeline_wrapper(question, session_id, summarizer_llm, generation_model=None, top_k=5):
    
    qdrant_client = QdrantClient(
        url=config.QDRANT_URL, # QDRANT_URL=http://qdrant:6333 when local, or web URL for Qdrant Cloud
        api_key=config.QDRANT_API_KEY  # For Qdrant Cloud only, empty otherwise
    )
        
    result = rag_pipeline(question, qdrant_client, session_id, generation_model, top_k)

    # Update memory with summarization
    add_message(session_id, "user", question, summarizer_llm)
    add_message(session_id, "assistant", result["answer"], summarizer_llm)

    # sources = [Source(**s) for s in result.get("sources", [])]


    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
    }