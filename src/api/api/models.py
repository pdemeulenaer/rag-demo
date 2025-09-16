from pydantic import BaseModel, Field
from typing import List, Any, Optional, Dict


class ChatMessage(BaseModel):
    role: str
    content: str

class RAGRequest(BaseModel):
    query: str = Field(..., description="The query to be used in the RAG pipeline")
    generation_model: Optional[str] = Field(
        None,
        description="Optional override for the generation model (e.g. gpt-4-nano, gpt-4-mini, gpt-5-nano)"
    )

# class RAGUsedImage(BaseModel):
#     image_url: str = Field(..., description="The URL of the image")
#     price: Optional[float] = Field(..., description="The price of the item")
#     description: str = Field(..., description="The description of the item")

class Source(BaseModel):
    id: str
    title: Optional[str] = None
    authors: list[str] = []
    year: Optional[int] = None
    page: int | list[int] | None


class RAGResponse(BaseModel):
    request_id: str = Field(..., description="The request ID")
    answer: str = Field(..., description="The content of the RAG response")
    chat_history: List[ChatMessage] = Field(..., description="The full conversation history")
    # used_image_urls: List[RAGUsedImage]
    sources: List[Source] = Field(..., description="The sources used in the RAG response")