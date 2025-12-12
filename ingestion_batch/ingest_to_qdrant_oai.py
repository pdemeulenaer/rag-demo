# ingestion_batch/ingest_to_qdrant_oai.py

import os
import httpx
import tempfile
import time

from src.api.core.config import config
from src.api.ingestion.ingest_documents import IngestionError, ingest_documents


# === Config ===
COLLECTION_NAME = "test_collection_oai_test_image" # "test_collection_oai_test_multilanguage" # test_collection_oai_prod
# PDF_FOLDER = os.path.join(os.path.dirname(__file__), "/../data/folder")
PDF_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/folder"))
URLS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ingestion_batch/url_list.txt"))


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


# === Ingestion Function for URLs ===
def ingest_urls_to_qdrant(urls_file_path: str, qdrant_url: str, qdrant_api_key: str, collection_name: str):
    """
    Reads a file containing a list of PDF URLs, downloads each PDF to a
    temporary file, and then ingests it using ingest_documents.
    """
    # 1. Check for URL file existence
    if not os.path.isfile(urls_file_path):
        print(f"❌ Error: URLs file not found at {urls_file_path}")
        return

    # 2. Read URLs from file
    with open(urls_file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"→ Found {len(urls)} URLs to process in {os.path.basename(urls_file_path)}")
    
    # 3. Process each URL
    for url in urls:
        print(f"\n🚀 Starting download and ingestion for: {url}")
        
        # Determine a filename for logging
        filename = url.split('/')[-1] if url else "unknown_url_file"

        # Use a temporary file to store the downloaded content
        # This keeps the core ingestion logic simpler as it still handles a file_path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            temp_filepath = tmp_file.name
            
            try:
                # Download the PDF content
                response = httpx.get(url, timeout=120)
                response.raise_for_status()
                
                # Write content to the temporary file
                tmp_file.write(response.content)
                
            except httpx.HTTPError as e:
                print(f"❌ Failed to download {url}: HTTP Error {response.status_code}")
                continue
            except Exception as e:
                print(f"❌ An unexpected error occurred during download of {url}: {e}")
                continue
        
        # 4. Ingest the temporary file
        try:
            # We assume ingest_documents is available and takes config as its fifth argument
            ingest_documents(
                file_path=temp_filepath, 
                qdrant_url=qdrant_url, 
                qdrant_api_key=qdrant_api_key, 
                collection_name=collection_name, 
                verbose=True
            )
        except IngestionError as e:
            print(f"⚠️ Failed to ingest {filename} (from URL): {e}")
        except Exception as e:
            print(f"🛑 Critical error processing {filename} (from URL): {e}")
        finally:
            # 5. Clean up the temporary file
            try:
                os.remove(temp_filepath)
                # print(f"✨ Cleaned up temporary file: {temp_filepath}")
            except OSError as e:
                print(f"⚠️ Error cleaning up temporary file {temp_filepath}: {e}")


if __name__ == "__main__":

    # Example 1: Ingest from local folder
    print("--- Starting Folder Ingestion ---")
    ingest_folder_to_qdrant(
        folder_path=PDF_FOLDER,
        qdrant_url=config.QDRANT_URL,
        qdrant_api_key=config.QDRANT_API_KEY,
        collection_name=COLLECTION_NAME,
    )   

    # # Example 2: Ingest from list of URLs
    # # Assuming 'url_list.txt' exists and contains one URL per line
    # print("\n--- Starting URL Ingestion ---")
    # ingest_urls_to_qdrant(
    #     urls_file_path=URLS_FILE,
    #     qdrant_url=config.QDRANT_URL,
    #     qdrant_api_key=config.QDRANT_API_KEY,
    #     collection_name=COLLECTION_NAME,
    # )        