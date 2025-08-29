from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging
from httpx import AsyncClient

from contextlib import asynccontextmanager
from src.api.core.config import settings
from src.api.api.middleware import RequestIDMiddleware
from src.api.api.endpoints import api_router
# from dotenv import load_dotenv

# load_dotenv()

import os
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