import os
from abc import ABC, abstractmethod
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timedelta, timezone
from azure.storage.blob import (
    BlobServiceClient, 
    generate_blob_sas, 
    BlobSasPermissions
)
from src.api.core.config import config

class StorageProvider(ABC):
    @abstractmethod
    def save_image(self, content: bytes, filename: str) -> str:
        """Saves image and returns the URL for the frontend."""
        pass

class LocalStorageProvider(StorageProvider):
    def save_image(self, content: bytes, filename: str) -> str:
        file_path = os.path.join(config.IMAGES_FOLDER, filename)
        with open(file_path, "wb") as f:
            f.write(content)
        # Return the relative path that our existing router converts to absolute
        return filename 

class AzureStorageProvider(StorageProvider):
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(
            config.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_name = config.AZURE_CONTAINER_NAME
        self.container_client = self.blob_service_client.get_container_client(
            self.container_name
        )

    def save_image(self, content: bytes, filename: str) -> str:
        # 1. Upload the blob
        blob_client = self.container_client.get_blob_client(filename)
        blob_client.upload_blob(content, overwrite=True)
        
        # 2. Return just the filename (or a path)
        # We will generate the temporary SAS token later in the RAG router
        return filename

    def generate_signed_url(self, filename: str, expiry_hours: int = 1) -> str:
        """
        Generates a temporary URL for a specific blob.
        expiry_hours: defaults to 1 for UI, but can be set to 24 for Batch API.
        """
        
        # 1. Strip any leading slashes or paths from the filename just in case
        # This turns "/api/images/fig.png" into "fig.png"
        clean_filename = os.path.basename(filename)

        # 2. Generate the SAS token
        sas_token = generate_blob_sas(
            account_name=self.blob_service_client.account_name,
            container_name=self.container_name,
            blob_name=clean_filename,
            account_key=self.blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            # Backdate start by 5 mins to avoid clock sync issues
            start=datetime.now(timezone.utc) - timedelta(minutes=5),
            expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        )

        # 3. Build the URL correctly
        # self.container_client.url usually looks like: 
        # https://account.blob.core.windows.net/container
        base_url = self.container_client.url.rstrip('/')
        
        return f"{base_url}/{clean_filename}?{sas_token}"    

def get_storage_provider() -> StorageProvider:
    if config.STORAGE_MODE.upper() == "AZURE":
        return AzureStorageProvider()
    return LocalStorageProvider()