"""Read-only, hash-verified full chunks under exact PostgreSQL snapshot scope."""
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from uuid import NAMESPACE_URL, uuid5

from .contracts import SourceChunk


class VerifiedReader:
    """Never fetch an arbitrary manifest URL. Container paths map to the host root."""

    def __init__(self, settings):
        self.root = settings.PAPERS_ARTIFACT_DIR.resolve()
        self.container = None
        if settings.PAPERS_STORAGE_MODE == "AZURE":
            from azure.storage.blob import BlobServiceClient
            service = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING)
            self.container = service.get_container_client(settings.PAPERS_AZURE_CONTAINER)

    def read(self, reference, build_id, name):
        digest = reference.get("sha256", "")
        size = reference.get("bytes")
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or type(size) is not int or size < 0:
            raise ValueError("Artifact reference has invalid hash or size")
        key = f"builds/{build_id}/{digest}/{name}"
        uri = str(reference.get("uri", ""))
        if self.container is not None:
            # Only the configured account/container may be read; SAS queries are unnecessary.
            actual, expected = urlsplit(uri), urlsplit(self.container.url)
            if (actual.scheme != "https" or actual.netloc != expected.netloc
                    or unquote(actual.path) != expected.path.rstrip("/") + "/" + key
                    or actual.query or actual.fragment):
                raise ValueError("Artifact is outside the configured Azure container")
            data = self.container.download_blob(key).readall()
        else:
            if not uri.endswith("/" + key) or urlsplit(uri).scheme:
                raise ValueError("Artifact path does not match its build/hash/name")
            path = (self.root / key).resolve()
            if not path.is_relative_to(self.root):
                raise ValueError("Artifact path escapes configured root")
            data = path.read_bytes()
        if len(data) != size or sha256(data).hexdigest() != digest:
            raise ValueError(f"Artifact integrity check failed: {build_id}/{name}")
        return data

    def read_json(self, reference, build_id, name):
        return json.loads(self.read(reference, build_id, name))


def load_paper(paper, catalogue, reader):
    """Frozen ready builds may be retained, but deleted papers are never eligible."""
    build_id = paper["build_id"]
    rows = catalogue.scoped_ready_builds(paper["collection"], [build_id], active_only=False)
    if len(rows) != 1:
        raise ValueError(f"Frozen build is not available/ready: {build_id}")
    row = rows[0]
    if (str(row["paper_id"]) != paper["paper_id"] or row["source"] != paper["source"]
            or row["version"] != paper["version"] or row["deleted"]):
        raise ValueError(f"Frozen paper identity/version is not eligible: {build_id}")
    manifest = row["manifest"]
    saved = reader.read_json(manifest["artifact"], build_id, "manifest.json")
    # Batch completion may include the previous manifest's artifact reference.
    if {k: v for k, v in saved.items() if k != "artifact"} != {
            key: value for key, value in manifest.items() if key != "artifact"}:
        raise ValueError("Saved manifest does not match the catalogue manifest")
    for key in ("collection", "pipeline_id", "embedding_model"):
        if manifest.get(key) != row[key]:
            raise ValueError(f"Manifest identity mismatch: {key}")
    if not all(key in manifest for key in ("text", "pages", "markdown", "extraction")):
        raise ValueError("Full structured artifacts are unavailable; migrate this build first")
    raw = reader.read_json(manifest["text"], build_id, "chunks.json")
    pages = reader.read_json(manifest["pages"], build_id, "pages.json")
    reader.read(manifest["markdown"], build_id, "document.md")
    order = manifest.get("chunk_order", {})
    if (not raw or order.get("count") != len(raw) or order.get("starts_at") != 0
            or order.get("field") != "chunk_index" or order.get("contiguous") is not True
            or order.get("scope") != "text_chunks"):
        raise ValueError("Manifest lacks a complete, contiguous text chunk order")
    if [chunk.get("chunk_index") for chunk in raw] != list(range(len(raw))):
        raise ValueError("Full chunk ordinals are not contiguous")
    point_ids = [str(uuid5(NAMESPACE_URL, f"{build_id}:{i}")) for i in range(len(raw))]
    if paper["source"] == "arxiv":
        if manifest.get("chunk_count") != len(raw):
            raise ValueError("arXiv text point count mismatch")
    else:
        payloads = reader.read_json(manifest["payloads"], build_id, "payloads.json")
        text = sorted((p for p in payloads if p["payload"].get("type") == "text"),
                      key=lambda p: p["payload"].get("chunk_index", -1))
        point_ids = [str(uuid5(NAMESPACE_URL, f"{build_id}:text:{i}")) for i in range(len(raw))]
        if len(text) != len(raw):
            raise ValueError("Upload text point count mismatch")
        for i, payload in enumerate(text):
            identity = payload["payload"]
            if (str(payload["id"]) != point_ids[i]
                    or point_ids[i] not in manifest["point_ids"]
                    or str(identity.get("paper_id")) != paper["paper_id"]
                    or str(identity.get("build_id")) != build_id
                    or identity.get("chunk_index") != i
                    or identity.get("source_text") != raw[i]["text"]):
                raise ValueError("Upload chunk/payload identity mismatch")
    chunks = []
    page_numbers = {page["page_number"] for page in pages}
    for chunk, point_id in zip(raw, point_ids):
        if chunk["page_number"] not in page_numbers:
            raise ValueError("Chunk page is absent from the verified pages artifact")
        chunks.append(SourceChunk.model_validate({
            key: paper[key] for key in ("paper_id", "build_id", "collection", "source")
        } | dict(point_id=point_id, page_number=chunk["page_number"],
                 section_header=chunk.get("section_header"), text=chunk["text"])))
    return chunks, manifest["artifact"]["sha256"]
