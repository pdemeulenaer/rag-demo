import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


# Get the root directory of your project (2 levels up from src/api/core/config.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Config(BaseSettings):

    # API Keys
    OPENAI_API_KEY: str
    GROQ_API_KEY: str
    QDRANT_API_KEY: str
    COHERE_API_KEY: str

    # Qdrant Settings
    QDRANT_URL: str
    QDRANT_COLLECTION_NAME: str 
    QDRANT_PORT: Optional[int] = None

    @property
    def qdrant_port(self) -> int:
        """Use Qdrant Cloud's HTTPS port unless a port is explicitly configured."""
        if self.QDRANT_PORT is not None:
            return self.QDRANT_PORT
        return 443 if self.QDRANT_URL.startswith("https://") else 6333

    # Model Settings (Defaults provided)
    EMBEDDING_MODEL: str
    EMBEDDING_MODEL_PROVIDER: str
    GENERATION_MODEL: str
    GENERATION_MODEL_PROVIDER: str

    # Bounded Agentic RAG planner. Answer synthesis still uses GENERATION_MODEL.
    AGENT_MODEL: str = "gpt-5-mini"
    AGENT_REASONING_EFFORT: str = "minimal"
    AGENT_MAX_COMPLETION_TOKENS: int = 2000
    AGENT_MAX_ROUNDS: int = 3
    AGENT_MAX_TOOL_CALLS: int = 12
    AGENT_MAX_EVIDENCE_CHUNKS: int = 30
    AGENT_MAX_ELAPSED_SECONDS: float = 120.0
    AGENT_MAX_PLANNER_TOKENS: int = 6000

    # Optional Langfuse observability. Disabled means a true no-op: the SDK is
    # not imported by the application tracing shim.
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "http://localhost:3000"
    LANGFUSE_ENVIRONMENT: str = "local"
    LANGFUSE_RELEASE: str = ""
    LANGFUSE_DATASET_PREFIX: str = "scientific-paper-rag"
    # EMBEDDING_API_URL: str
    


    # Static settings (not from env)
    # ==============================

    # Embedding model settings
    EMBEDDING_MODEL='text-embedding-3-small'
    EMBEDDING_MODEL_PROVIDER='openai'

    # Generation model settings
    GENERATION_MODEL='gpt-4.1-nano' # 'gpt-4.1-mini' #'gpt-5-nano' 'llama-3.3-70b-versatile' 'gpt-5-mini' 'gpt-4.1' 'openai/gpt-oss-120b'
    GENERATION_MODEL_PROVIDER='openai' # 'groq' # 'openai'
    GENERATION_MODEL_TEMPERATURE: float = 0.5
    GENERATION_MODEL_MAX_TOKENS: int = 4096 # previously 1024 but too small for complex answers
    RAG_PROMPT_TEMPLATE_PATH: str = "src/api/rag/prompts/rag_generation.yaml"    

    # Ingestion settings
    QDRANT_COLLECTION_NAME: str = 'uploaded_papers_v2'

    SUMMARIZATION_MODEL: str = 'llama-3.1-8b-instant' # 'llama-3.3-70b-versatile'
    SUMMARIZATION_PROMPT: str = 'Summarize the following text: {{text}}'
    SUMMARIZATION_MODEL_TEMPERATURE: float = 0.3
    SUMMARIZATION_MODEL_MAX_TOKENS: int = 256
    # SUMMARIZATION_PROMPT_TEMPLATE_PATH: str =

    METADATA_MODEL: str = 'gpt-4.1-nano' # 'llama-3.3-70b-versatile'    
    METADATA_MODEL_TEMPERATURE: float = 0
    METADATA_MODEL_MAX_TOKENS: int = 500
    # METADATA_PROMPT_TEMPLATE_PATH: str =
    
    EXTERNAL_API_URL: str = "http://localhost:8000" # Default for local dev

    # Storage settings
    STORAGE_MODE: str = "LOCAL" # "LOCAL" or "AZURE"
    # We define the folder relative to the BASE_DIR
    # This results in /app/src/api/data/images inside Docker
    # and [your_path]/src/api/data/images locally.
    IMAGES_FOLDER: str = str(BASE_DIR / "src" / "api" / "data" / "images")    
    # ingestion batch threshold: above the threshold, use batch OpenAI API
    INGESTION_BATCH_THRESHOLD: int = 2
    IMAGE_DESCRIPTION_PROMPT_TEMPLATE_PATH: str = "src/api/rag/prompts/document_ingestion.yaml"
    IMAGE_DESCRIPTION_MODEL: str = "gpt-4.1-mini" #"gpt-4o-mini", #"gpt-4o", 

    # Azure Settings (only needed if STORAGE_MODE == "AZURE")
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_CONTAINER_NAME: str = "rag-images"
    
    # This is the public URL of your storage account or CDN
    # e.g., https://mystorage.blob.core.windows.net/rag-images
    AZURE_STORAGE_PUBLIC_URL: Optional[str] = None   

    # Redis Settings
    # When running in Docker, this will be 'redis'. 
    # When running locally, it defaults to 'localhost'.
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0  

    # model_config = SettingsConfigDict(env_file=".env")
    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore", # Prevents crashes if extra vars are in .env
        case_sensitive=False # Allows REDIS_HOST or redis_host in .env
        )

class Settings(BaseSettings):
    DEFAULT_TIMEOUT: float = 30.0
    VERSION: str = "0.1.0"

config = Config()
settings = Settings()
