from fastapi import APIRouter, Request, Response
import logging
import uuid
import openai
import instructor

from pydantic import BaseModel

from src.api.core.config import config
from src.api.utils import get_conversation_chain, get_reranked_qdrant_retriever
from src.api.rag.intent_router import classify_question
from src.api.rag import metadata_handlers as mh
from src.api.rag.retrieval import rag_pipeline_wrapper, get_memory
from src.api.api.models import RAGRequest, RAGResponse, ChatMessage #, RAGUsedImage


# Initialize the summarizer LLM using instructor with Groq
summarizer_llm = instructor.from_openai(
    openai.OpenAI(api_key=config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
)

logger = logging.getLogger(__name__)

rag_router = APIRouter()



# Global conversation object (simple stateful example)
conversation = None

class QuestionRequest(BaseModel):
    question: str

# @rag_router.post("/connect")
# async def connect_to_knowledge_base():
#     global conversation
#     try:
#         retriever = get_reranked_qdrant_retriever()
#         conversation = get_conversation_chain(retriever)
#         return {"status": "connected"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


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


    if intent.intent != "mixed":
        # structured / metadata path
        if intent.intent == "list_titles":
            answer = "\n".join(mh.list_titles())
        elif intent.intent == "list_authors":
            answer = "\n".join(mh.list_authors())
        elif intent.intent == "titles_by_author":
            answer = "\n".join(mh.titles_by_author(intent.author, intent.year))
        elif intent.intent == "authors_by_year":
            answer = "\n".join(mh.titles_by_author(None, intent.year))
        elif intent.intent == "author_of_title":
            answer = ", ".join(mh.author_of_title(intent.title))
        elif intent.intent == "summarize_paper":
            answer = mh.summarize_paper(intent.title)
        else:
            answer = "I couldn’t classify that question."

        return RAGResponse(
            request_id=request.state.request_id,
            answer=answer,
            chat_history=[],   # you can choose to include memory if you like
            sources=[]
        )            


    # Run the RAG pipeline with session-based memory
    result = rag_pipeline_wrapper(payload.query, 
                                  session_id, 
                                  summarizer_llm,
                                  generation_model=gen_model
                                  )

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
        answer=result["answer"],
        chat_history=full_history,
        sources=result.get("sources", [])
    )    



# api_router = APIRouter()
# api_router.include_router(rag_router, tags=["rag"])
# api_router.include_router(ingestion_router, tags=["ingestion"]) # Include the new router
