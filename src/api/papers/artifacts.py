"""Versioned, content-addressed artifacts; local disk is only for local demos."""
from hashlib import sha256
import json


class ArtifactStore:
    def __init__(self, settings):
        self.settings = settings
        self.container = None
        if settings.PAPERS_STORAGE_MODE == "AZURE":
            from azure.storage.blob import BlobServiceClient
            if not settings.AZURE_STORAGE_CONNECTION_STRING:
                raise ValueError("Azure artifact storage requires a connection string")
            self.container = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            ).get_container_client(settings.PAPERS_AZURE_CONTAINER)
            # Explicitly provision a private container beforehand; no public ACL changes.
            self.container.get_container_properties()

    def put(self, build_id, name, data):
        digest = sha256(data).hexdigest()
        key = f"builds/{build_id}/{digest}/{name}"
        if self.container is not None:
            from azure.core.exceptions import ResourceExistsError
            try:
                self.container.upload_blob(key, data, overwrite=False)
            except ResourceExistsError:
                pass
            uri = self.container.url.split("?", 1)[0] + "/" + key
        else:
            path = self.settings.PAPERS_ARTIFACT_DIR / key
            path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic replacement at an immutable content-derived key.
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_bytes(data)
            temporary.replace(path)
            uri = str(path.resolve())
        return {"uri": uri, "sha256": digest, "bytes": len(data)}

    def put_json(self, build_id, name, value):
        return self.put(build_id, name, json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
