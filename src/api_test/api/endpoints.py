from fastapi import APIRouter, Request, HTTPException
import logging

from pydantic import BaseModel
from dotenv import load_dotenv
from src.api_test.utils import get_conversation_chain, get_reranked_qdrant_retriever

from src.api_test.rag.retrieval import rag_pipeline_wrapper
from src.api_test.api.models import RAGRequest, RAGResponse #, RAGUsedImage

load_dotenv()

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
    payload: RAGRequest
) -> RAGResponse:

    result = rag_pipeline_wrapper(payload.query)
    # used_image_urls = [RAGUsedImage(image_url=image["image_url"], price=image["price"], description=image["description"]) for image in result["retrieved_images"]]

    return RAGResponse(
        request_id=request.state.request_id,
        answer=result["answer"],
        # used_image_urls=used_image_urls
    )


api_router = APIRouter()
api_router.include_router(rag_router, tags=["rag"])
