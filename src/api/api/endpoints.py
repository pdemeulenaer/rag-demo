from fastapi import APIRouter, Request, HTTPException, Response
import logging
import uuid
import json

from pydantic import BaseModel

from src.api.core.config import config
from src.api.utils import get_conversation_chain, get_reranked_qdrant_retriever

import openai
import instructor

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

@rag_router.post("/connect")
async def connect_to_knowledge_base():
    global conversation
    try:
        retriever = get_reranked_qdrant_retriever()
        conversation = get_conversation_chain(retriever)
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/rag")
async def ask_question(request: QuestionRequest):
    global conversation
        
    if conversation is None:
        try:
            # connect_to_knowledge_base()
            retriever = get_reranked_qdrant_retriever()
            conversation = get_conversation_chain(retriever)            
        except Exception as e:
            raise HTTPException(status_code=400, detail="Knowledge base not connected.")  
    
    try:
        
        result = conversation({"question": request.question})
        return {
            "answer": result["chat_history"][-1].content,
            "chat_history": [
                {"role": msg.type, "content": msg.content}
                for msg in result["chat_history"]
            ]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()  # Print full stack trace
        raise HTTPException(status_code=500, detail=f"Answering failed: {str(e)}")



@rag_router.post("/rag2")
async def rag(
    request: Request,
    payload: RAGRequest,
    response: Response  # <-- Added here so you can set cookies
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

    # Run the RAG pipeline with session-based memory
    result = rag_pipeline_wrapper(payload.query, session_id, summarizer_llm)

    # # Build and return the RAGResponse
    # return RAGResponse(
    #     request_id=request.state.request_id,
    #     answer=result["answer"],
    # )

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



api_router = APIRouter()
api_router.include_router(rag_router, tags=["rag"])
