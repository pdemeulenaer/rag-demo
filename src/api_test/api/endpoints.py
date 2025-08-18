from fastapi import APIRouter, Request, HTTPException, Response
import logging
import uuid
import json

from pydantic import BaseModel
# from dotenv import load_dotenv

from src.api_test.core.config import config
from src.api_test.utils import get_conversation_chain, get_reranked_qdrant_retriever

import openai
import instructor

from src.api_test.rag.retrieval import rag_pipeline_wrapper, get_memory
from src.api_test.api.models import RAGRequest, RAGResponse, ChatMessage #, RAGUsedImage
# import os
# from src.api_test.core.config import config

# load_dotenv()

# os.environ["LANGCHAIN_TRACING_V2"] = "true" if config.LANGSMITH_TRACING else "false"
# os.environ["LANGCHAIN_ENDPOINT"] = config.LANGSMITH_ENDPOINT
# os.environ["LANGCHAIN_API_KEY"] = config.LANGSMITH_API_KEY
# os.environ["LANGCHAIN_PROJECT"] = config.LANGSMITH_PROJECT

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


# @rag_router.post("/rag2")
# async def rag(
#     request: Request,
#     payload: RAGRequest,
# ) -> RAGResponse:

    

#     session_id = request.cookies.get("session_id")
#     if not session_id:
#         session_id = str(uuid.uuid4())
#         response.set_cookie(key="session_id", value=session_id)

#     result = rag_pipeline_wrapper(payload.query, session_id, summarizer_llm)

#     # result = rag_pipeline_wrapper(payload.query)
#     # used_image_urls = [RAGUsedImage(image_url=image["image_url"], price=image["price"], description=image["description"]) for image in result["retrieved_images"]]

#     return RAGResponse(
#         request_id=request.state.request_id,
#         answer=result["answer"],
#         # used_image_urls=used_image_urls
#     )



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
        chat_history=full_history
    )    



api_router = APIRouter()
api_router.include_router(rag_router, tags=["rag"])
