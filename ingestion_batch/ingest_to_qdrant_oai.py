# ingestion_batch/ingest_to_qdrant_oai.py

import os

from src.api.core.config import config
from src.api.ingestion.ingest_documents import IngestionError, ingest_documents


# === Config ===
COLLECTION_NAME = "test_collection_oai_prod"
# PDF_FOLDER = os.path.join(os.path.dirname(__file__), "/../data/folder")
PDF_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/folder"))


# === Ingestion Function ===
def ingest_folder_to_qdrant(folder_path: str, qdrant_url: str, qdrant_api_key: str, collection_name: str):
    """
    Wrapper function to iterate over a local folder and ingest each PDF.
    """
    if not os.path.isdir(folder_path):
        print(f"❌ Error: Folder not found at {folder_path}")
        return

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(folder_path, filename)
            try:
                # Call the single-document ingestion function, passing config
                ingest_documents(
                    file_path=filepath, 
                    qdrant_url=qdrant_url, 
                    qdrant_api_key=qdrant_api_key, 
                    collection_name=collection_name, 
                    verbose=True
                )
            except IngestionError as e:
                print(f"⚠️ Failed to ingest {filename}: {e}")
            except Exception as e:
                print(f"🛑 Critical error processing {filename}: {e}")


if __name__ == "__main__":
    ingest_folder_to_qdrant(
        folder_path=PDF_FOLDER,
        qdrant_url=config.QDRANT_URL,
        qdrant_api_key=config.QDRANT_API_KEY,
        collection_name=COLLECTION_NAME,
    )    