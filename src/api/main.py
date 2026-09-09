# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
from httpx import AsyncClient

from contextlib import asynccontextmanager
from src.api.core.config import settings
from src.api.api.middleware import RequestIDMiddleware
from src.api.api.rag_router import rag_router
from src.api.api.ingestion_router import router as ingestion_router
from src.api.api.system_router import router as system_router
from src.api.api.papers_router import router as papers_router
from src.api.core.config import config

# This must be the first thing your app does!
os.environ["LANGCHAIN_TRACING_V2"] = "true" if config.LANGSMITH_TRACING else "false"
os.environ["LANGCHAIN_ENDPOINT"] = config.LANGSMITH_ENDPOINT
os.environ["LANGCHAIN_API_KEY"] = config.LANGSMITH_API_KEY
os.environ["LANGCHAIN_PROJECT"] = config.LANGSMITH_PROJECT


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

client = AsyncClient(timeout=settings.DEFAULT_TIMEOUT)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Middleware to handle the lifecycle of the FastAPI app.
    It is called when the application starts up and shuts down.
    """    
    logger.info("Application starting up...")

    yield

    logger.info("Application shutting down...")
    await client.aclose()

app = FastAPI(lifespan=lifespan)

# --- MOUNT STATIC FILES HERE ---
# This links the physical folder to the URL path /api/images
# app.mount("/api/images", StaticFiles(directory=config.IMAGES_FOLDER), name="images")

os.makedirs(config.IMAGES_FOLDER, exist_ok=True)
app.mount("/api/images", StaticFiles(directory=config.IMAGES_FOLDER), name="images")

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers in the main application instance
app.include_router(system_router, tags=["system"])
app.include_router(rag_router, tags=["rag"])
app.include_router(ingestion_router, tags=["ingestion"])
app.include_router(papers_router, tags=["papers"])

@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {"message": "API"}
