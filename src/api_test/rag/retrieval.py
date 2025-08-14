import os
import openai
import instructor
from openai import OpenAI
from groq import Groq
from pydantic import BaseModel
from typing import List
import json

from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, Filter, FieldCondition, MatchText, FusionQuery
from langsmith import traceable, get_current_run_tree

from src.api_test.core.config import config
from src.api_test.rag.utils.utils import prompt_template_config, prompt_template_registry




# Initialize the conversation memory
conversation_memory = {}

class ConversationMemory:
    def __init__(self, window_size=2):
        self.recent_messages = []
        self.summary = ""
        self.window_size = window_size

# def summarize_messages(messages, summarizer_llm):
#     """Summarize older messages into a concise running summary."""
#     text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages])
#     prompt = f"Summarize the following conversation history concisely:\n\n{text}\n\nSummary:"

#     response, raw_response = summarizer_llm.chat.completions.create_with_completion(
#         model="llama-3.3-70b-versatile",
#         response_model=str,  # Expect plain text
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.5
#     )

#     return response.strip()

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
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        response_model=RAGSummarizationResponse,
        max_tokens=500
    )

    # return response.choices[0].message.content.strip()
    return response.summary.strip()


def get_memory(session_id: str) -> ConversationMemory:
    if session_id not in conversation_memory:
        conversation_memory[session_id] = ConversationMemory()
    return conversation_memory[session_id]

def add_message(session_id: str, role: str, content: str, summarizer_llm):
    memory = get_memory(session_id)
    memory.recent_messages.append({"role": role, "content": content})

    # Summarize older messages if buffer exceeded
    if len(memory.recent_messages) > memory.window_size:
        old_messages = memory.recent_messages[:-memory.window_size]
        summary_update = summarize_messages(old_messages, summarizer_llm)
        memory.summary += " " + summary_update
        memory.recent_messages = memory.recent_messages[-memory.window_size:]





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

    retrieved_context_ids = []
    retrieved_context = []
    similarity_scores = []

    for result in results.points:
        retrieved_context_ids.append(result.id)
        retrieved_context.append(result.payload['text'])
        similarity_scores.append(result.score)

    return {
        "retrieved_context_ids": retrieved_context_ids,
        "retrieved_context": retrieved_context,
        "similarity_scores": similarity_scores
    }


@traceable(
    name="format_retrieved_context",
    run_type="prompt"
)
def process_context(context):

    formatted_context = ""

    for id, chunk in zip(context["retrieved_context_ids"], context["retrieved_context"]):
        formatted_context += f"- {id}: {chunk}\n"

    return formatted_context


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "The answer to the question based on the provided context.",
        },
        "retrieved_context_ids": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string", #"integer",
                        "description": "The index of the chunk that was used to answer the question.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Short description of the item based on the context together with the id.",
                    },
                },
            },
        },
    },
}

@traceable(
    name="render_prompt",
    run_type="prompt"
)
# def build_prompt(context, question):

#     processed_context = process_context(context)

#     prompt_template = prompt_template_config(config.RAG_PROMPT_TEMPLATE_PATH, "rag_generation")
#     # prompt_template = prompt_template_registry("rag-prompt") # Prompt registry in LangSmith

#     prompt = prompt_template.render(processed_context=processed_context, question=question, output_json_schema=json.dumps(OUTPUT_SCHEMA, indent=2))

#     return prompt
def build_prompt(context, question, session_id):
    memory = get_memory(session_id)

    formatted_recent = "\n".join(
        [f"{msg['role'].capitalize()}: {msg['content']}" for msg in memory.recent_messages]
    )

    full_history = f"Conversation Summary:\n{memory.summary}\n\nRecent Messages:\n{formatted_recent}"

    processed_context = process_context(context)
    # prompt_template = prompt_template_registry("rag-prompt")
    prompt_template = prompt_template_config(config.RAG_PROMPT_TEMPLATE_PATH, "rag_generation")

    prompt = prompt_template.render(
        conversation_history=full_history,
        processed_context=processed_context,
        question=question,
        output_json_schema=json.dumps(OUTPUT_SCHEMA, indent=2)
    )

    return prompt



class RAGUsedContext(BaseModel):
    id: str #int # changed from Aurimas' code since here we use uuid as strings
    description: str


class RAGGenerationResponse(BaseModel):
    answer: str
    retrieved_context_ids: List[RAGUsedContext]

class RAGSummarizationResponse(BaseModel):
    summary: str    



@traceable(
    name="generate_answer",
    run_type="llm",
    metadata={"ls_provider": config.GENERATION_MODEL_PROVIDER, "ls_model_name": config.GENERATION_MODEL}
)
def generate_answer(prompt):

    client = instructor.from_openai(OpenAI(api_key=config.OPENAI_API_KEY))
    response, raw_response = client.chat.completions.create_with_completion(
        model="gpt-4.1",
        response_model=RAGGenerationResponse,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
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
    name="generate_answer",
    run_type="llm",
    metadata={"ls_provider": "Groq", "ls_model_name": "llama-3.3-70b-versatile"}
)
def generate_answer_groq(prompt):    

    # Initialize the Groq client
    groq_client = Groq(api_key=config.GROQ_API_KEY)

    # Patch the Groq client with instructor
    client = instructor.from_groq(groq_client)

    # Use the instructor-patched Groq client for chat completions
    response, raw_response = client.chat.completions.create_with_completion(
        model="llama-3.3-70b-versatile",
        response_model=RAGGenerationResponse,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
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
)
# def rag_pipeline(question, qdrant_client, top_k=5):

#     retrieved_context = retrieve_context(question, qdrant_client, top_k)
#     prompt = build_prompt(retrieved_context, question)
#     # answer = generate_answer(prompt)
#     answer = generate_answer_groq(prompt)
    

#     final_result = {
#         "answer": answer,
#         "question": question,
#         "retrieved_context_ids": retrieved_context["retrieved_context_ids"],
#         "retrieved_context": retrieved_context["retrieved_context"],
#         "similarity_scores": retrieved_context["similarity_scores"]
#     }

#     return final_result
def rag_pipeline(question, qdrant_client, session_id, top_k=5):
    retrieved_context = retrieve_context(question, qdrant_client, top_k)
    prompt = build_prompt(retrieved_context, question, session_id)
    answer = generate_answer_groq(prompt)

    return {
        "answer": answer,
        "question": question,
        "retrieved_context_ids": retrieved_context["retrieved_context_ids"],
        "retrieved_context": retrieved_context["retrieved_context"],
        "similarity_scores": retrieved_context["similarity_scores"]
    }



def rag_pipeline_wrapper(question, session_id, summarizer_llm, top_k=5):
# def rag_pipeline_wrapper(question, session_id, top_k=5):
    # qdrant_client = QdrantClient(url=config.QDRANT_URL)
    qdrant_client = QdrantClient(
        url=config.QDRANT_URL,
        api_key=config.QDRANT_API_KEY  # Add this line
    )
        
    result = rag_pipeline(question, qdrant_client, session_id, top_k)

    # Update memory with summarization
    add_message(session_id, "user", question, summarizer_llm)
    add_message(session_id, "assistant", result["answer"].answer, summarizer_llm)

    # image_url_list = []
    # for id in result["answer"].retrieved_context_ids:
    #     payload = qdrant_client.retrieve(
    #         collection_name=config.QDRANT_COLLECTION_NAME,
    #         ids=[id.id]
    #     )[0].payload
    #     image_url = payload.get("first_large_image")
    #     price = payload.get("price")
    #     if image_url:
    #         image_url_list.append({"image_url": image_url, "price": price, "description": id.description})

    return {
        "answer": result["answer"].answer,
        # "retrieved_images": image_url_list
    }


# def rag_pipeline_wrapper(question, top_k=5):
#     # Ensure QDRANT_API_KEY is loaded from your config
#     qdrant_client = QdrantClient(
#         url=config.QDRANT_URL,
#         api_key=config.QDRANT_API_KEY  # Add this line
#     )

#     result = rag_pipeline(question, qdrant_client, top_k)
# # def rag_pipeline_wrapper(question, top_k=5):

# #     qdrant_client = QdrantClient(url=config.QDRANT_URL)

# #     result = rag_pipeline(question, qdrant_client, top_k)

#     # image_url_list = []
#     # for id in result["answer"].retrieved_context_ids:
#     #     payload = qdrant_client.retrieve(
#     #         collection_name=config.QDRANT_COLLECTION_NAME,
#     #         ids=[id.id]
#     #     )[0].payload
#     #     # image_url = payload.get("first_large_image")
#     #     # price = payload.get("price")
#     #     # if image_url:
#     #     #     image_url_list.append({"image_url": image_url, "price": price, "description": id.description})

#     return {
#         "answer": result["answer"].answer,
#         # "retrieved_images": image_url_list
#     }