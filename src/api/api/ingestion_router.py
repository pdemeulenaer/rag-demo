# src/api/api/ingestion_router.py

from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List
import os
import tempfile
import logging

from src.api.core.config import config
from src.api.ingestion.ingest_documents import ingest_documents, IngestionError

ingestion_router = APIRouter()
logger = logging.getLogger(__name__)

@ingestion_router.post("/ingest")
async def ingest_files(files: List[UploadFile] = File(...)):
    """
    Ingests one or more PDF files uploaded by the user.
    """
    if not files:
        logger.error("No files uploaded.")
        raise HTTPException(status_code=400, detail="No files uploaded")

    logger.info(f"Received {len(files)} file(s) for ingestion.")

    # Use a temporary directory to save the uploaded files
    # This is a good practice to handle file processing without
    # cluttering the main application's file system.
    with tempfile.TemporaryDirectory() as temp_dir:
        ingested_count = 0
        failed_files = []

        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            logger.info(f"Processing file: {file.filename}")
            try:
                # Save the uploaded file chunk by chunk to the temp directory
                # This is memory-efficient and handles large files.
                with open(file_path, "wb") as buffer:
                    logger.info(f"Saving file to {file_path}")
                    while True:
                        chunk = await file.read(1024 * 1024) # Read in 1MB chunks
                        if not chunk:
                            break
                        buffer.write(chunk)

                logger.info(f"File {file.filename} saved successfully.")                        

                # Call the ingestion function
                logger.info(f"Calling ingest_documents for {file.filename}.")
                ingest_documents(
                    file_path=file_path,
                    qdrant_url=config.QDRANT_URL,
                    qdrant_api_key=config.QDRANT_API_KEY,
                    collection_name=config.QDRANT_COLLECTION_NAME
                )
                logger.info(f"Ingestion successful for {file.filename}.")
                ingested_count += 1

            except IngestionError as e:
                logger.error(f"IngestionError for {file.filename}: {e}")
                failed_files.append({"filename": file.filename, "error": str(e)})
            except Exception as e:
                logger.exception(f"An unexpected error occurred while processing {file.filename}")
                failed_files.append({"filename": file.filename, "error": f"An unexpected error occurred: {e}"})

    if failed_files:
        logger.error(f"Failed to ingest some files: {failed_files}")
        raise HTTPException(status_code=500, detail={"message": f"Ingested {ingested_count} file(s). Failed to ingest: {failed_files}"})

    logger.info(f"Successfully ingested {ingested_count} document(s).")
    return {"message": f"Successfully ingested {ingested_count} document(s)."}