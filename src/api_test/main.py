from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import logging
from httpx import AsyncClient

from contextlib import asynccontextmanager
from src.api_test.core.config import settings
from src.api_test.api.middleware import RequestIDMiddleware
from src.api_test.api.endpoints import api_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

client = AsyncClient(timeout=settings.DEFAULT_TIMEOUT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")

    yield

    logger.info("Application shutting down...")
    await client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {"message": "API"}






from pydantic import BaseModel
from dotenv import load_dotenv
from src.api_test.utils import get_conversation_chain, get_reranked_qdrant_retriever

load_dotenv()

# Global conversation object (simple stateful example)
conversation = None

class QuestionRequest(BaseModel):
    question: str

@app.post("/connect")
def connect_to_knowledge_base():
    global conversation
    try:
        retriever = get_reranked_qdrant_retriever()
        conversation = get_conversation_chain(retriever)
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def ask_question(request: QuestionRequest):
    global conversation
        
    if conversation is None:
        try:
            connect_to_knowledge_base()
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

