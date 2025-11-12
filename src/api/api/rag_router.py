# src/api/api/rag_router.py
from fastapi import APIRouter, Request, Response
import logging
import uuid
import openai
import instructor
from pydantic import BaseModel

from src.api.core.config import config
from src.api.rag.intent_router import classify_question
from src.api.rag import metadata_handlers as mh
from src.api.rag.retrieval import rag_pipeline_wrapper, get_memory, add_message
from src.api.api.models import RAGRequest, RAGResponse, ChatMessage #, RAGUsedImage

logger = logging.getLogger(__name__)


class ChatFollowupResponse(BaseModel):
    answer: str

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


# Initialize the summarizer LLM using instructor with Groq
summarizer_llm = instructor.from_openai(
    openai.OpenAI(api_key=config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
)

rag_router = APIRouter()

class QuestionRequest(BaseModel):
    question: str

@rag_router.post("/rag2")
async def rag(
    request: Request,
    payload: RAGRequest,
    response: Response
) -> RAGResponse:

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

    # Retrieve chat memory
    chat_history = chat_memory(session_id) 

    # ---- NEW: classify intent ----
    user_q = payload.query
    intent = classify_question(user_q, chat_history)
    logger.info(f"Intent: {intent}")
    logger.info("Classifier output: %s", intent.model_dump() if hasattr(intent,"model_dump") else intent)

    # Depending on intent, 
    if intent.intent != "rag":
        # structured / metadata path
        if intent.intent == "list_titles":
            answer = mh.list_titles() #"\n".join(mh.list_titles())
            sources=[]

        elif intent.intent == "list_authors":
            answer = mh.list_authors() #"\n".join(mh.list_authors())
            sources=[]

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

                return RAGResponse(
                    request_id=request.state.request_id,
                    answer=result["answer"],
                    chat_history=full_history,
                    sources=result.get("sources", [])
                )
                # answer=result["answer"]
                # sources=result.get("sources", [])
            else:
                answer = mh.titles_by_author(intent.author, intent.year)
                sources=[]

        elif intent.intent == "authors_by_year":
            answer = mh.titles_by_author(None, intent.year)
            sources=[]

        elif intent.intent == "author_of_title":
            answer = mh.author_of_title(intent.title)
            sources=[]

        elif intent.intent == "summarize_paper":
            answer = mh.summarize_paper(intent.title)
            sources=[]

        elif intent.intent == "chat_followup":
            logger.info("Handling chat_followup intent via local context reasoning")
            chat_history = chat_memory(session_id)
            answer = answer_from_chat_context(user_q, chat_history)
            sources = []            

        else:
            answer = "I couldn't classify that question."
            sources=[]
            logger.warning(f"Unrecognized intent: {intent.intent}")

        answer = format_answer_for_display(answer)

    else: # Use the RAG

        # Run the RAG pipeline with session-based memory
        result = rag_pipeline_wrapper(payload.query, 
                                    session_id, 
                                    generation_model=gen_model
                                    )        
        answer = result["answer"]
        sources = result.get("sources", [])

    # Update memory with summarization
    add_message(session_id, "user", user_q)
    add_message(session_id, "assistant", answer)

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
        sources=sources
    )    