from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.api_test.utils import get_conversation_chain, get_reranked_qdrant_retriever

app = FastAPI()

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
        raise HTTPException(status_code=500, detail=str(e))
