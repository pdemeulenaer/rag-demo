import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Get the root directory of your project (2 levels up from src/api/core/config.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
class Config(BaseSettings):
    OPENAI_API_KEY: str
    GROQ_API_KEY: str
    # GOOGLE_API_KEY: str
    QDRANT_URL: str
    QDRANT_API_KEY: str    
    QDRANT_COLLECTION_NAME: str 
    EMBEDDING_MODEL: str
    EMBEDDING_MODEL_PROVIDER: str
    GENERATION_MODEL: str
    GENERATION_MODEL_PROVIDER: str
    LANGSMITH_TRACING: bool
    LANGSMITH_ENDPOINT: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str    
    EMBEDDING_API_URL: str
    COHERE_API_KEY: str

    # We define the folder relative to the BASE_DIR
    # This results in /app/src/api/data/images inside Docker
    # and [your_path]/src/api/data/images locally.
    IMAGES_FOLDER: str = str(BASE_DIR / "src" / "api" / "data" / "images")

    # Static settings (not from env)
    # ==============================

    # Embedding model settings
    EMBEDDING_MODEL='text-embedding-3-small'
    EMBEDDING_MODEL_PROVIDER='openai'

    # Generation model settings
    GENERATION_MODEL='gpt-4.1-nano' # 'gpt-4.1-mini' #'gpt-5-nano' 'llama-3.3-70b-versatile' 'gpt-5-mini' 'gpt-4.1' 'openai/gpt-oss-120b'
    GENERATION_MODEL_PROVIDER='openai' # 'groq' # 'openai'
    GENERATION_MODEL_TEMPERATURE: float = 0.5
    GENERATION_MODEL_MAX_TOKENS: int = 1024
    RAG_PROMPT_TEMPLATE_PATH: str = "src/api/rag/prompts/rag_generation.yaml"    

    # Langsmith settings
    LANGSMITH_TRACING=False #false for testing, true in production
    LANGSMITH_ENDPOINT='https://api.smith.langchain.com'
    LANGSMITH_PROJECT='rag-tracing'

    # Ingestion settings
    QDRANT_COLLECTION_NAME: str = 'test_collection_oai_test_image' # 'test_collection_oai_test_summary' # test_collection_oai_prod # test_collection_oai_local2

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

    # model_config = SettingsConfigDict(env_file=".env")
    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore" # Prevents crashes if extra vars are in .env
        )

class Settings(BaseSettings):
    DEFAULT_TIMEOUT: float = 30.0
    VERSION: str = "0.1.0"

config = Config()
settings = Settings()