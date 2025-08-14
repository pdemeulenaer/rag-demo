#!/bin/bash

# Load environment variables from .env file
source .env

# Run your application with Uvicorn
uv run uvicorn src.api_test.main:app --reload --port 8000