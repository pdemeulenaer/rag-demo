# src/api/rag/summarize.py

import logging
# import httpx
from openai import OpenAI
import instructor
from pydantic import BaseModel

from src.api.core.config import config
from src.api.rag.utils.utils import prompt_template_config

logger = logging.getLogger(__name__)


class SummarizationResponse(BaseModel):
    summary: str

def summarize_text(
    summary: str,
    provider: str = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    template_name: str = None,
) -> SummarizationResponse:
    """
    Generic summarization function for both OpenAI and Groq models.

    Args:
        summary (str): The text to summarize (conversation, document, etc.).
        provider (str): "openai" or "groq". Defaults to config.SUMMARIZATION_PROVIDER.
        model (str): Model name. Defaults to config.SUMMARIZATION_MODEL.
        temperature (float): Sampling temperature. Defaults to config.SUMMARIZATION_MODEL_TEMPERATURE.
        max_tokens (int): Max tokens in summary. Defaults to config.SUMMARIZATION_MODEL_MAX_TOKENS.
        template_name (str): Name of the prompt template to use. Defaults to "summarization".

    Returns:
        SummarizationResponse: Pydantic model containing the summarized text.
    """

    provider = provider or getattr(config, "SUMMARIZATION_PROVIDER", "groq")
    model = model or config.SUMMARIZATION_MODEL
    temperature = temperature or config.SUMMARIZATION_MODEL_TEMPERATURE
    max_tokens = max_tokens or config.SUMMARIZATION_MODEL_MAX_TOKENS
    template_name = template_name or "summarization"

    # --- 1️⃣ Load the prompt template ---
    prompt_template = prompt_template_config(config.RAG_PROMPT_TEMPLATE_PATH, template_name)

    system_prompt = prompt_template["system"].render(summary=summary)
    user_prompt = prompt_template["user"].render(summary=summary)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    logger.info(f"Summarization model: {provider}/{model}")
    logger.info(f"Prompt template used: {template_name}")
    logger.info(f"Prompt length: {len(system_prompt) + len(user_prompt)}")

    # --- 2️⃣ Handle provider-specific calls ---
    try:
        if provider.lower() == "openai":
            client = instructor.from_openai(OpenAI(api_key=config.OPENAI_API_KEY))

        elif provider.lower() == "groq":
            if not config.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY is not set in environment variables.")

            client = instructor.from_openai(
                OpenAI(
                    api_key=config.GROQ_API_KEY,
                    base_url="https://api.groq.com/openai/v1",                    
                ),
                mode=instructor.Mode.JSON # make sure to use JSON mode for structured responses
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_model=SummarizationResponse,
            response_format={"type": "json_object"},
        )

        # Instructor automatically parses JSON into your Pydantic model
        logger.debug(f"Output summary length: {len(response.summary)}")
        return response

    except Exception as e:
        logger.error(f"Summarization failed ({provider}): {e}")
        fallback_summary = f"[Summarization failed — returning truncated input] {summary[:200]}..."
        return SummarizationResponse(summary=fallback_summary)    


    # try:
    #     if provider.lower() == "openai":
    #         client = OpenAI(api_key=config.OPENAI_API_KEY)

    #         response = client.chat.completions.create(
    #             model=model,
    #             messages=messages,
    #             temperature=temperature,
    #             max_tokens=max_tokens,
    #             response_model=SummarizationResponse,
    #         )
    #         summary_text = response.choices[0].message.content.strip()

    #     elif provider.lower() == "groq":
    #         api_key = config.GROQ_API_KEY
    #         if not api_key:
    #             raise ValueError("GROQ_API_KEY is not set in environment variables.")

    #         headers = {
    #             "Authorization": f"Bearer {api_key}",
    #             "Content-Type": "application/json",
    #         }
    #         payload = {
    #             "model": model,
    #             "messages": messages,
    #             "temperature": temperature,
    #             "max_tokens": max_tokens,
    #         }

    #         response = httpx.post(
    #             "https://api.groq.com/openai/v1/chat/completions",
    #             headers=headers,
    #             json=payload,
    #             timeout=60,
    #         )
    #         response.raise_for_status()
    #         summary_text = response.json()["choices"][0]["message"]["content"].strip()

    #     else:
    #         raise ValueError(f"Unsupported provider: {provider}")

    #     logger.debug(f"Output summary length: {len(summary_text)}")
    #     return SummarizationResponse(summary=summary_text)

    # except Exception as e:
    #     logger.error(f"Summarization failed ({provider}): {e}")
    #     # fallback_summary = summary[:200] + "..."
    #     fallback_summary = f"[Summarization failed — returning truncated input] {summary[:200]}..."
    #     return SummarizationResponse(summary=fallback_summary)







# # THIS FROM RETRIEVAL.PY
# class RAGSummarizationResponse(BaseModel):
#     summary: str  

# def summarize_messages(messages, summarizer_llm):
#     """
#     Summarizes the conversation history using the given LLM client (Groq in this case).
#     This version works without Instructor's create_with_completion.
#     """
#     # Convert messages list to a readable string
#     formatted_messages = "\n".join(
#         [f"{m['role'].capitalize()}: {m['content']}" for m in messages]
#     )

#     prompt = f"""
#     Please summarize the following conversation briefly, preserving key facts, names, and context
#     so that future turns can be understood without losing important details.
    
#     Conversation:
#     {formatted_messages}
#     """

#     response = summarizer_llm.chat.completions.create(
#         model=config.SUMMARIZATION_MODEL, # "llama-3.3-70b-versatile",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=config.SUMMARIZATION_MODEL_TEMPERATURE, # 0.5,
#         response_model=RAGSummarizationResponse,
#         max_tokens=config.SUMMARIZATION_MODEL_MAX_TOKENS # 1000
#     )
#     return response.summary.strip()


# # THIS FROM ingest_documents.py
# def summarize_chunk(text: str) -> str:
#     """
#     Use Groq's Mixtral model to summarize a long chunk of text.
#     """
#     api_key = config.GROQ_API_KEY # os.getenv("GROQ_API_KEY")
#     if not api_key:
#         raise ValueError("GROQ_API_KEY is not set in environment variables.")

#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "model": config.SUMMARIZATION_MODEL,
#         "messages": [
#             {"role": "system", "content": "You are a helpful assistant that summarizes academic documents."},
#             {"role": "user", "content": f"Summarize the following chunk:\n\n{text}"}
#         ],
#         "temperature": config.SUMMARIZATION_MODEL_TEMPERATURE, 
#         "max_tokens": config.SUMMARIZATION_MODEL_MAX_TOKENS 
#     }

#     try:
#         response = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
#         response.raise_for_status()
#         return response.json()["choices"][0]["message"]["content"].strip()
#     except Exception as e:
#         print(f"⚠️ Groq summarization failed: {e}")
#         return text[:200] + "..."




# import instructor
# from openai import OpenAI
# from pydantic import BaseModel, Field
# from typing import List, Dict, Optional, Any

# # Define the Pydantic model needed for structured chat summarization
# class RAGSummarizationResponse(BaseModel):
#     """The summarized context of the previous conversation."""
#     summary: str = Field(description="A concise summary of the conversation history.")

# # --- General Summarization Function ---
# def generate_summary(
#     text_to_summarize: str | List[Dict[str, str]],
#     client: OpenAI,
#     model_name: str,
#     temperature: float,
#     max_tokens: int,
#     is_chat_history: bool = False,
#     system_prompt: Optional[str] = None,
#     response_model: Optional[BaseModel] = None,
# ) -> str:
#     """
#     Generates a summary using the provided OpenAI-compatible client (OpenAI or Groq).
#     (The body of this function remains the same as provided in the previous response.)
#     """
#     if not client:
#         raise ValueError("An initialized LLM client must be provided.")

#     if is_chat_history and isinstance(text_to_summarize, list):
#         # Case 1: Chat History Summarization (Messages List Input)
#         formatted_messages = "\n".join(
#             [f"{m['role'].capitalize()}: {m['content']}" for m in text_to_summarize]
#         )
#         user_content = f"""
#         Please summarize the following conversation briefly, preserving key facts, names, and context
#         so that future turns can be understood without losing important details.
        
#         Conversation:
#         {formatted_messages}
#         """
#         messages = [{"role": "user", "content": user_content}]
        
#         if response_model is None:
#              raise ValueError("Chat history summarization requires a Pydantic response_model.")
        
#     elif isinstance(text_to_summarize, str):
#         # Case 2: Unstructured Text Summarization (String Input)
#         user_content = f"Summarize the following chunk:\n\n{text_to_summarize}"
#         messages = [
#             {"role": "system", "content": system_prompt or "You are a helpful assistant that summarizes academic documents."},
#             {"role": "user", "content": user_content}
#         ]
        
#     else:
#         raise ValueError("Input must be a string (for chunks) or a list of messages (for chat history).")

#     try:
#         response = client.chat.completions.create(
#             model=model_name,
#             messages=messages,
#             temperature=temperature,
#             max_tokens=max_tokens,
#             response_model=response_model, 
#             timeout=60
#         )
        
#         if is_chat_history and response_model:
#             return response.summary.strip()
#         else:
#             return response.choices[0].message.content.strip()
            
#     except Exception as e:
#         print(f"⚠️ Summarization with model '{model_name}' failed: {e}")
#         if isinstance(text_to_summarize, str):
#             return text_to_summarize[:200] + "..."
#         return "[Error: Failed to summarize conversation.]"