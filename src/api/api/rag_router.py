# src/api/api/rag_router.py
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import FileResponse
import os
import logging
import uuid
import openai
import instructor
from typing import List
from pydantic import BaseModel

from src.api.core.config import config
from src.api.rag.intent_router import classify_question
from src.api.rag import metadata_handlers as mh
from src.api.rag.retrieval import rag_pipeline_wrapper, get_memory, add_message
from src.api.api.models import RAGRequest, RAGResponse, ChatMessage #, RAGUsedImage
from src.api.core.storage import get_storage_provider

logger = logging.getLogger(__name__)

# Define where images are stored (import from config)
IMAGES_DIR = config.IMAGES_FOLDER


class ChatFollowupResponse(BaseModel):
    answer: str

class QuestionRequest(BaseModel):
    question: str


# # Initialize the summarizer LLM using instructor with Groq
# summarizer_llm = instructor.from_openai(
#     openai.OpenAI(api_key=config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
# )


# --- Helper Functions ---

def answer_from_chat_context(question: str, chat_history: str, model="gpt-4o-mini") -> str:
    """
    Use the chat history alone to answer the user's follow-up question.
    Does not trigger RAG or metadata retrieval.
    TODO: USE TEMPLATE FROM YAML TEMPLATE FILE!
    TODO: GENERALIZE TO GROQ LLM
    """

    llm = instructor.from_openai(
        openai.OpenAI(api_key=config.OPENAI_API_KEY)
    )

    system_prompt = (
        "You are a helpful scientific assistant. Answer the user's question based "
        "only on the following chat history. Do not invent or retrieve new information "
        "from outside the conversation context."
    )

    user_prompt = f"""
    Chat history:
    {chat_history}

    Current user question:
    {question}
    """

    response = llm.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_model=ChatFollowupResponse,
    )

    return response.answer.strip()  # instructor will handle parsing to string


def format_answer_for_display(ans) -> str:
    """
    Accepts either a string or a list of strings and returns
    a numbered Markdown list if there is more than one line/item.
    """
    if ans is None:
        return ""

    # If we already have a list or tuple, treat each item as a line
    if isinstance(ans, (list, tuple)):
        lines = [str(l).strip() for l in ans if str(l).strip()]
    else:
        lines = [l.strip() for l in str(ans).splitlines() if l.strip()]

    if len(lines) > 1:
        return "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
    return lines[0] if lines else ""


def chat_memory(session_id: str) -> str:
    """
    Retrieve and format the user's chat memory for LLM context classification.

    Combines:
      - A high-level conversation summary (if available)
      - The recent chat messages (as maintained in memory.recent_messages)

    Returns:
        A compact text block suitable for injection into an LLM prompt.
    """
    
    memory = get_memory(session_id)

    # Format recent messages
    formatted_recent = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}"
        for msg in memory.recent_messages
    )

    # Combine summary + recent messages
    parts = []
    if memory.summary:
        parts.append(f"Conversation Summary:\n{memory.summary.strip()}")
    if formatted_recent:
        parts.append(f"Recent Messages:\n{formatted_recent}")

    return "\n\n".join(parts).strip()


# def _process_images(raw_images: list, request: Request) -> list:
#     """
#     Helper to convert relative image URLs returned by the pipeline 
#     into absolute URLs that the frontend can reach.
#     """
#     processed_images = []
    
#     for img in raw_images:
#         # Get just the filename (e.g., figure_1.png) from the stored path
#         filename = os.path.basename(img.get("url", ""))
        
#         # request.base_url provides "http://localhost:8000/"
#         # We append "api/images/" to match the mount above
#         absolute_url = f"{str(request.base_url).rstrip('/')}/api/images/{filename}"
        
#         # request.base_url provides "http://localhost:8000/"
#         # We append "api/images/" to match the mount above
#         absolute_url = f"{str(request.base_url).rstrip('/')}/api/images/{filename}"
        
#         processed_images.append({
#             "url": absolute_url,
#             "caption": img.get("caption", ""),
#             "page": img.get("page"),
#             "file_title": img.get("file_title", "")
#         })
#     return processed_images

# def _process_images(raw_images: list, request: Request) -> list:
#     processed_images = []
    
#     # We ignore request.base_url because it returns 'http://api:8000' in Docker
#     # We use the URL that the browser actually understands
#     base_url = config.EXTERNAL_API_URL.rstrip("/")

#     for img in raw_images:
#         filename = os.path.basename(img.get("url", ""))
        
#         # This will now correctly result in http://localhost:8000/api/images/...
#         absolute_url = f"{base_url}/api/images/{filename}"
        
#         processed_images.append({
#             "url": absolute_url,
#             "caption": img.get("caption", ""),
#             "page": img.get("page"),
#             "file_title": img.get("file_title", "")
#         })
        
#     return processed_images
def _process_images(raw_images: list, request: Request) -> list:
    processed_images = []
    storage = get_storage_provider()
    
    for img in raw_images:
        # This is the 'hash_fig1.png' from Qdrant
        db_path = img.get("url", "") 
        
        if config.STORAGE_MODE.upper() == "AZURE":
            # The provider now handles the full URL building
            final_url = storage.generate_signed_url(db_path)
        else:
            # Local mode still needs the local API prefix
            base_url = config.EXTERNAL_API_URL.rstrip("/")
            filename = os.path.basename(db_path)
            final_url = f"{base_url}/api/images/{filename}"
            
        processed_images.append({
            "url": final_url,
            "caption": img.get("caption", ""),
            "page": img.get("page"),
            "file_title": img.get("file_title", "")
        })
    return processed_images


# --- Router ---

rag_router = APIRouter()


@rag_router.get("/images/{image_name}")
async def get_image(image_name: str, request: Request):
    # Security: Prevent directory traversal attacks
    if ".." in image_name or "/" in image_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    image_path = os.path.join(IMAGES_DIR, image_name)
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    # Optional: Check request.cookies.get("session_id") here if you want private access
    
    return FileResponse(image_path)


@rag_router.post("/rag2")
async def rag(
    request: Request,
    payload: RAGRequest,
    response: Response
) -> RAGResponse:

    # 1. Session Management
    # Get or create a session_id cookie
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,      # Prevents JS access
            secure=False,       # Change to True in production (HTTPS)
            samesite="lax"      # Adjust as needed
        )

    # Determine generation model (user-selected or default)
    gen_model = payload.generation_model or config.GENERATION_MODEL
    
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Generation model: {gen_model}")

    # 2. Intent Classification

    # Retrieve chat memory
    chat_history = chat_memory(session_id) 
    user_q = payload.query
    intent = classify_question(user_q, chat_history)
    logger.info(f"Intent: {intent}")
    logger.info("Classifier output: %s", intent.model_dump() if hasattr(intent,"model_dump") else intent)

    # Initialize outputs
    answer = ""
    sources = []
    rag_images = []

    # 3. Execution Logic
    # Depending on intent, 
    if intent.intent != "rag":
        # --- Metadata / Structured Intents ---
        if intent.intent == "list_titles":
            answer = mh.list_titles()
        elif intent.intent == "list_authors":
            answer = mh.list_authors()
        elif intent.intent == "authors_by_year":
            answer = mh.titles_by_author(None, intent.year)
        elif intent.intent == "author_of_title":
            answer = mh.author_of_title(intent.title)
        elif intent.intent == "summarize_paper":
            answer = mh.summarize_paper(intent.title)
        elif intent.intent == "chat_followup":
            logger.info("Handling chat_followup intent via local context reasoning")
            answer = answer_from_chat_context(user_q, chat_history)

        elif intent.intent == "titles_by_author":
            if not intent.author:
                # ❗ Intent router said titles_by_author but didn’t give an author → fallback to RAG
                logger.info("No author extracted for titles_by_author → falling back to semantic RAG")
                result = rag_pipeline_wrapper(user_q, session_id, generation_model=gen_model)

                # Update memory with summarization
                add_message(session_id, "user", user_q)
                add_message(session_id, "assistant", result['answer'])

                # Retrieve the full conversation memory
                memory = get_memory(session_id)
                
                # Create the chat history by combining the summary and recent messages
                # This is a good way to represent the full history in a serializable format
                full_history = []
                if memory.summary:
                    full_history.append({"role": "system", "content": memory.summary})
                    
                for msg in memory.recent_messages:
                    full_history.append({"role": msg["role"], "content": msg["content"]})

                answer = result["answer"]
                sources = result.get("sources", [])

                # Process images for the fallback path too
                rag_images = _process_images(result.get("images", []), request)

            else:
                answer = mh.titles_by_author(intent.author, intent.year)

        else:
            answer = "I couldn't classify that question."
            logger.warning(f"Unrecognized intent: {intent.intent}")

        # # Format list-based answers
        # if intent.intent != "titles_by_author" or (intent.intent == "titles_by_author" and intent.author):
        #     answer = format_answer_for_display(answer)
        answer = format_answer_for_display(answer)

    else: # Use the RAG
        # --- Standard RAG Intent ---
        # Run the RAG pipeline with session-based memory
        result = rag_pipeline_wrapper(user_q,
                                      session_id,
                                      generation_model=gen_model
                                      )        
        answer = result["answer"]
        sources = result.get("sources", [])

        # Process images returned by the pipeline
        rag_images = _process_images(result.get("images", []), request)

    # 4. Memory Update
    add_message(session_id, "user", user_q)
    add_message(session_id, "assistant", answer)

    # 5. Build Final History for Response
    # Retrieve the full conversation memory
    memory = get_memory(session_id)    
    # Create the chat history by combining the summary and recent messages
    # This is a good way to represent the full history in a serializable format
    full_history = []
    if memory.summary:
        full_history.append({"role": "system", "content": memory.summary})        
    for msg in memory.recent_messages:
        full_history.append({"role": msg["role"], "content": msg["content"]})

    # Build and return the RAGResponse, including the chat_history
    return RAGResponse(
        request_id=request.state.request_id,
        answer=answer,
        chat_history=full_history,
        sources=sources,
        images=rag_images
    )    