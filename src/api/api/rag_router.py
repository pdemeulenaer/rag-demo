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

# def format_answer_for_display(ans) -> str:
#     """
#     Format an answer for display as Markdown bullets.
#     - If `ans` is a list, each item becomes a bullet.
#     - If `ans` is a string with multiple lines, each line becomes a bullet.
#     - If `ans` is a single string, return as-is.
#     """
#     if isinstance(ans, list):
#         return "\n".join(f"- {a}" for a in ans if a)
#     elif isinstance(ans, str):
#         lines = [l.strip() for l in ans.splitlines() if l.strip()]
#         if len(lines) > 1:
#             return "\n".join(f"- {l}" for l in lines)
#         return ans
#     return str(ans)
# def format_answer_for_display(ans: str) -> str:
#     """If `ans` has multiple non-empty lines, format as a numbered Markdown list."""
#     lines = [l.strip() for l in ans.splitlines() if l.strip()]
#     if len(lines) > 1:
#         # 1-based numbering for Markdown
#         return "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
#     return ans
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
    

    # ---- NEW: classify intent ----
    user_q = payload.query
    intent = classify_question(user_q)
    logger.info(f"Intent: {intent}")
    logger.info("Classifier output: %s", intent.model_dump() if hasattr(intent,"model_dump") else intent)

    # Depending on intent, 
    if intent.intent != "mixed":
        # structured / metadata path
        if intent.intent == "list_titles":
            answer = mh.list_titles() #"\n".join(mh.list_titles())
            sources=[]

        elif intent.intent == "list_authors":
            answer = mh.list_authors() #"\n".join(mh.list_authors())
            sources=[]

        elif intent.intent == "titles_by_author":
            if not intent.author:
                # ❗ router said titles_by_author but didn’t give an author → fallback to RAG
                logger.info("No author extracted for titles_by_author → falling back to semantic RAG")
                result = rag_pipeline_wrapper(user_q, session_id, generation_model=gen_model)

                # Update memory with summarization
                add_message(session_id, "user", user_q, summarizer_llm)
                add_message(session_id, "assistant", result['answer'], summarizer_llm)

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
                answer = mh.titles_by_author(intent.author, intent.year) #"\n".join(mh.titles_by_author(intent.author, intent.year))
                sources=[]

        elif intent.intent == "authors_by_year":
            answer = mh.titles_by_author(None, intent.year) #"\n".join(mh.titles_by_author(None, intent.year))
            sources=[]

        elif intent.intent == "author_of_title":
            answer = mh.author_of_title(intent.title) #", ".join(mh.author_of_title(intent.title))
            sources=[]

        elif intent.intent == "summarize_paper":
            answer = mh.summarize_paper(intent.title)
            sources=[]

        else:
            answer = "I couldn’t classify that question."
            sources=[]

        # return RAGResponse(
        #     request_id=request.state.request_id,
        #     answer=format_answer_for_display(answer),
        #     chat_history=[],   # you can choose to include memory if you like
        #     sources=[]
        # )    
        answer = format_answer_for_display(answer)

    else: # Use the RAG as intent is not "mixed"

        # Run the RAG pipeline with session-based memory
        result = rag_pipeline_wrapper(payload.query, 
                                    session_id, 
                                    generation_model=gen_model
                                    )        
        answer = result["answer"]
        sources = result.get("sources", [])

    # Update memory with summarization
    add_message(session_id, "user", user_q, summarizer_llm)
    add_message(session_id, "assistant", answer, summarizer_llm)

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