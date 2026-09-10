"""Catalogue-backed upload ingestion, including durable Batch completion state."""
import base64
from contextlib import closing
from hashlib import sha256
import io
import json
import logging
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models as m

from .artifacts import ArtifactStore
from .catalogue import Catalogue
from .consistency import activate_verified
from .settings import PaperSettings


def qdrant_client():
    from src.api.core.config import config
    return QdrantClient(url=config.QDRANT_URL, port=config.qdrant_port,
        api_key=config.QDRANT_API_KEY or None, timeout=30, check_compatibility=False)


def pipeline_id(mode):
    from src.api.core.config import config
    spec = ["upload-v2", mode, config.EMBEDDING_MODEL, config.IMAGE_DESCRIPTION_MODEL,
            config.SUMMARIZATION_MODEL,
            "metadata:openai/gpt-oss-20b", "pymupdf:4000/400",
            sha256(Path(config.IMAGE_DESCRIPTION_PROMPT_TEMPLATE_PATH).read_bytes()).hexdigest()]
    return sha256(json.dumps(spec).encode()).hexdigest()[:16]


def register_upload(catalogue, path, mode):
    from src.api.core.config import config
    digest = sha256(Path(path).read_bytes()).hexdigest()
    # Already adopted/indexed content needs neither another model call nor new vectors.
    for build in catalogue.all_builds():
        if (build["source"] == "uploads" and build["source_id"] == f"upload:{digest}"
                and build["active_build"] == build["id"] and build["status"] == "ready"
                and build["collection"] == config.QDRANT_COLLECTION_NAME
                and build["embedding_model"] == config.EMBEDDING_MODEL and not build["deleted"]):
            return build
    meta = {"title": Path(path).name, "file_name": Path(path).name,
            "file_hash": digest, "version": 1, "authors": []}
    return catalogue.upload(digest, meta, config.QDRANT_COLLECTION_NAME,
                            config.EMBEDDING_MODEL, pipeline_id(mode))


def make_payload(build, meta, text, kind, page=None, caption=None, image_path=None):
    return {"build_id": build["id"], "paper_id": build["paper_id"], "paper_version": build["version"],
            "file_hash": build["metadata"]["file_hash"], "file_name": build["metadata"]["file_name"],
            "file_title": meta.title, "authors": meta.authors, "keywords": meta.keywords,
            "year": meta.publication_year, "type": kind, "text": text,
            "page_number": page, "page": page, "caption": caption, "image_path": image_path}


def point_id(build, label):
    return str(uuid5(NAMESPACE_URL, f"{build['id']}:{label}"))


def upsert_payloads(client, build, payloads, embed):
    for start in range(0, len(payloads), 32):
        batch = payloads[start:start + 32]
        vectors = embed([row["payload"]["text"] for row in batch])
        if len(vectors) != len(batch):
            raise ValueError("Incomplete embedding batch")
        if not client.collection_exists(build["collection"]):
            client.create_collection(build["collection"], vectors_config=m.VectorParams(size=len(vectors[0]), distance=m.Distance.COSINE))
        client.create_payload_index(build["collection"], "build_id", m.PayloadSchemaType.KEYWORD, wait=True)
        client.create_payload_index(build["collection"], "text", m.PayloadSchemaType.TEXT, wait=True)
        client.upsert(build["collection"], [m.PointStruct(id=row["id"], payload=row["payload"], vector=vector)
            for row, vector in zip(batch, vectors)], wait=True)


def process_upload(catalogue, qdrant, build, path, mode, store, extract, metadata, describe, embed, storage, openai_client, template, summarize=None):
    """Any extraction, figure, embedding or upsert failure keeps this build inactive."""
    if build["status"] in {"ready", "running", "waiting_batch"}:
        return
    if build["attempts"] >= PaperSettings().ARXIV_MAX_ATTEMPTS:
        raise ValueError("Upload attempt budget exhausted; operator review required")
    catalogue.start(build["id"])
    try:
        data = Path(path).read_bytes()
        if sha256(data).hexdigest() != build["metadata"]["file_hash"]:
            raise ValueError("Upload content changed after registration")
        source = store.put(build["id"], "source.pdf", data)
        chunks, images, first_pages, _ = extract(path, build["metadata"]["file_hash"])
        if not chunks:
            raise ValueError("PDF has no extractable text")
        meta = metadata(first_pages)
        payloads = []
        for i, (text, page) in enumerate(chunks):
            summary = summarize(text) if mode == "sync" and summarize else ""
            searchable = f"Title: {meta.title}\nAuthors: {', '.join(meta.authors)}\nSummary: {summary}\nContent: {text}"
            payload = make_payload(build, meta, searchable, "chunk", page)
            payload["summary"] = summary
            payloads.append({"id": point_id(build, f"text:{i}"), "payload": payload})
        payloads.append({"id": point_id(build, "summary"),
                         "payload": make_payload(build, meta, meta.summary, "summary", 0)})
        image_tasks = {}
        figure_artifacts = []
        for index, image in enumerate(images):
            filename = f"{build['id']}_{Path(image['filename']).name}"
            storage.save_image(image["bytes"], filename)  # Propagate storage failures.
            image_artifact = store.put(build["id"], filename, image["bytes"])
            figure_artifacts.append(image_artifact)
            label = f"figure:{index}"
            payload = make_payload(build, meta, "", "figure", image["page_number"], image["caption"], filename)
            base64_image = base64.b64encode(image["bytes"]).decode()
            task = {"id": point_id(build, label), "payload": payload, "artifact": image_artifact}
            if mode == "batch":
                task["request"] = {"custom_id": task["id"], "method": "POST", "url": "/v1/chat/completions",
                    "body": {"model": template["model"], "max_tokens": 300, "messages": [
                        {"role": "system", "content": template["system"]},
                        {"role": "user", "content": [
                            {"type": "text", "text": template["user"].render(caption=image["caption"])},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]}]}}
                image_tasks[task["id"]] = task
            else:
                description = describe(base64_image, image["caption"])
                if not description:
                    raise ValueError("Empty figure description")
                payload["text"] = f"Figure: {image['caption']}\nDescription: {description}"
                payloads.append({"id": task["id"], "payload": payload})
        expected = [row["id"] for row in payloads] + list(image_tasks)
        manifest = {"source": source, "chunk_count": len(expected), "point_ids": expected,
            "pipeline_id": build["pipeline_id"], "embedding_model": build["embedding_model"],
            "figures": figure_artifacts,
            "payloads": store.put_json(build["id"], "payloads.json", payloads),
            "figure_tasks": {key: {k: v for k, v in task.items() if k != "request"} for key, task in image_tasks.items()}}
        updated_metadata = {**build["metadata"], "title": meta.title, "authors": meta.authors,
                            "year": meta.publication_year, "summary": meta.summary}
        catalogue.update_build(build["id"], manifest=manifest, metadata=updated_metadata)
        upsert_payloads(qdrant, build, payloads, embed)
        if image_tasks:
            data = "\n".join(json.dumps(task["request"]) for task in image_tasks.values()).encode()
            input_artifact = store.put(build["id"], "batch-input.jsonl", data)
            manifest["batch_input"] = input_artifact
            catalogue.update_build(build["id"], manifest=manifest)
            remote_file = openai_client.files.create(file=("figures.jsonl", io.BytesIO(data)), purpose="batch")
            manifest["batch_input_file_id"] = remote_file.id
            catalogue.update_build(build["id"], manifest=manifest)
            batch = openai_client.batches.create(input_file_id=remote_file.id,
                endpoint="/v1/chat/completions", completion_window="24h")
            manifest.update(batch_id=batch.id, batch_input=input_artifact)
            catalogue.update_build(build["id"], manifest=manifest, status="waiting_batch")
        else:
            manifest["artifact"] = store.put_json(build["id"], "manifest.json", manifest)
            activate_verified(catalogue, qdrant, build, manifest)
    except Exception as exc:
        catalogue.fail(build["id"], type(exc).__name__)
        raise


def complete_batch(catalogue, qdrant, build, output, embed, store=None):
    manifest = dict(build["manifest"])
    tasks = manifest["figure_tasks"]
    results = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = row.get("custom_id")
        if key not in tasks or key in results or row.get("error") or row.get("response", {}).get("status_code") != 200:
            raise ValueError("Unexpected, duplicate or failed batch result")
        description = row["response"]["body"]["choices"][0]["message"]["content"]
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Empty figure response")
        payload = {**tasks[key]["payload"], "text": f"Figure: {tasks[key]['payload']['caption']}\nDescription: {description}"}
        results[key] = {"id": key, "payload": payload}
    if set(results) != set(tasks):
        raise ValueError("Batch is missing expected figure results")
    if store is not None:
        manifest["figure_payloads"] = store.put_json(build["id"], "figure-payloads.json", list(results.values()))
        manifest["batch_output"] = store.put(build["id"], "batch-output.jsonl", output.encode())
        manifest["artifact"] = store.put_json(build["id"], "manifest.json", manifest)
        catalogue.update_build(build["id"], manifest=manifest)
    upsert_payloads(qdrant, build, list(results.values()), embed)
    activate_verified(catalogue, qdrant, build, manifest)


def run_uploads(file_paths, mode):
    from src.api.core.config import config
    from src.api.core.storage import get_storage_provider
    from src.api.ingestion.ingest_documents import extract_raw_content, extract_metadata_fast, describe_image_with_gpt4o, robust_summarize_text, OpenAIEmbeddings, client
    from src.api.rag.utils.utils import prompt_template_config
    settings = PaperSettings()
    catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
    try:
        with catalogue.writer_lock(), closing(qdrant_client()) as qdrant:
            catalogue.require_schema()
            store = ArtifactStore(settings)
            prompts = prompt_template_config(config.IMAGE_DESCRIPTION_PROMPT_TEMPLATE_PATH, "image_description_generation")
            embedding = OpenAIEmbeddings(model_name=settings.EMBEDDING_MODEL)
            for path in file_paths:
                build = register_upload(catalogue, path, mode)
                try:
                    process_upload(catalogue, qdrant, build, path, mode, store,
                        extract_raw_content, extract_metadata_fast, describe_image_with_gpt4o,
                        embedding.embed_documents, get_storage_provider(), client,
                        {"system": prompts["system"].render(), "user": prompts["user"], "model": config.IMAGE_DESCRIPTION_MODEL},
                        summarize=robust_summarize_text)
                except Exception as exc:
                    logging.getLogger(__name__).error("Upload build %s failed (%s); see catalogue", build["id"], type(exc).__name__)
    finally:
        catalogue.close()


def poll_batches(catalogue, qdrant, client, embed, store=None):
    """Batch association is durable in PostgreSQL, not expiring Redis metadata."""
    for build in catalogue.all_builds():
        if build["source"] != "uploads" or build["status"] != "waiting_batch":
            continue
        batch = client.batches.retrieve(build["manifest"]["batch_id"])
        if batch.status in {"failed", "expired", "cancelled"}:
            catalogue.fail(build["id"], f"batch_{batch.status}")
        elif batch.status == "completed":
            try:
                if batch.error_file_id or not batch.output_file_id:
                    raise ValueError("Batch contains errors or lacks output")
                complete_batch(catalogue, qdrant, build, client.files.content(batch.output_file_id).text, embed, store)
            except Exception as exc:
                catalogue.fail(build["id"], type(exc).__name__)
