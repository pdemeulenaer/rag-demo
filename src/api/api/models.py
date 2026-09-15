from pydantic import BaseModel, Field
from typing import List, Any, Optional, Dict, Union, Literal


class ChatMessage(BaseModel):
    role: str
    content: str

class RAGRequest(BaseModel):
    query: str = Field(..., description="The query to be used in the RAG pipeline")
    mode: Literal["vanilla", "hybrid"] | None = None
    corpus: Literal["uploads", "arxiv"] = "uploads"
    corpus_snapshot: str | None = None
    generation_model: Optional[str] = Field(
        None,
        description="Optional override for the generation model (e.g. gpt-4-nano, gpt-4-mini, gpt-5-nano)"
    )

# class RAGUsedImage(BaseModel):
#     image_url: str = Field(..., description="The URL of the image")
#     price: Optional[float] = Field(..., description="The price of the item")
#     description: str = Field(..., description="The description of the item")

class RAGImage(BaseModel):
    url: str
    caption: str = ""
    page: Union[list[int], int, None] = None
    file_title: str = ""

class Source(BaseModel):
    id: str
    paper_id: str | None = None
    arxiv_id: str | None = None
    paper_version: int | None = None
    source_url: str | None = None
    title: Optional[str] = None
    authors: list[str] = []
    year: Optional[int] = None
    page: int | list[int] | None


class RAGResponse(BaseModel):
    mode: str | None = None
    corpus_snapshot: str | None = None
    request_id: str = Field(..., description="The request ID")
    answer: str = Field(..., description="The content of the RAG response")
    chat_history: List[ChatMessage] = Field(..., description="The full conversation history")
    # used_image_urls: List[RAGUsedImage]
    sources: List[Source] = Field(..., description="The sources used in the RAG response")
    images: List[RAGImage] = []
