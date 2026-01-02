# src/api/api/ingestion_router.py

from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List, Dict, Any
import os
import tempfile
import logging
from qdrant_client import QdrantClient

from src.api.core.config import config
from src.api.ingestion.ingest_documents import ingest_documents #, IngestionError

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

            # except IngestionError as e:
            #     logger.error(f"IngestionError for {file.filename}: {e}")
            #     failed_files.append({"filename": file.filename, "error": str(e)})
            except Exception as e:
                logger.exception(f"An unexpected error occurred while processing {file.filename}")
                failed_files.append({"filename": file.filename, "error": f"An unexpected error occurred: {e}"})

    if failed_files:
        logger.error(f"Failed to ingest some files: {failed_files}")
        raise HTTPException(status_code=500, detail={"message": f"Ingested {ingested_count} file(s). Failed to ingest: {failed_files}"})

    logger.info(f"Successfully ingested {ingested_count} document(s).")
    return {"message": f"Successfully ingested {ingested_count} document(s)."}



@ingestion_router.get("/documents")
async def get_all_document_titles():
    """
    Retrieves a list of all unique document titles from the Qdrant collection.
    """
    try:
        qdrant_client = QdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY
        )
        collection_name = config.QDRANT_COLLECTION_NAME

        # Check if the collection exists before trying to access it
        if not qdrant_client.collection_exists(collection_name=collection_name):
            raise HTTPException(status_code=404, detail="Qdrant collection not found.")

        # Use a set to store unique titles
        unique_titles = set()
        
        offset = None
        while True:
            # Scroll through the collection in batches
            # The `with_payload=True` is the default, but we specify a list
            # of payload fields to retrieve for efficiency
            points, next_offset = qdrant_client.scroll(
                collection_name=collection_name,
                limit=100,  # Fetch 100 points at a time
                with_payload=["file_title"],
                with_vectors=False, # We don't need the vectors, so don't retrieve them
                offset=offset,
            )

            for point in points:
                title = point.payload.get("file_title")
                if title:
                    unique_titles.add(title)
            
            # If there's no next offset, we've reached the end of the collection
            if next_offset is None:
                break
            offset = next_offset

        # Convert the set to a sorted list for a consistent output
        titles_list = sorted(list(unique_titles))
        
        return {
            "total_documents": len(titles_list),
            "titles": titles_list
        }

    except Exception as e:
        logger.error(f"Failed to retrieve document titles: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document titles.")
