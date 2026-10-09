"""Frozen local inputs and crash-safe per-chunk checkpoints; no graph publication."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from time import monotonic

from .contracts import ExtractionBatch, SourceChunk


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@contextmanager
def directory_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another KG command is using this output directory") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def prepare(directory, selection, catalogue, reader, settings, *, paper_limit=None):
    from .artifacts import load_paper
    from .extraction import REVISION, LIBRARY_VERSION
    if paper_limit is not None and paper_limit < 1:
        raise ValueError("Paper limit must be positive")
    papers = selection["papers"][:paper_limit]
    chunks, manifests = [], {}
    for paper in papers:
        loaded, digest = load_paper(paper, catalogue, reader)
        chunks.extend(chunk.model_dump(mode="json") for chunk in loaded)
        manifests[paper["build_id"]] = digest
    plan = dict(schema_version=1, scope="verified_frozen_catalogue_builds",
                corpus_fingerprint=selection["corpus_fingerprint"], papers=papers,
                manifest_hashes=manifests, chunks=chunks, extraction_revision=REVISION,
                library_version=LIBRARY_VERSION, model=settings.KG_MODEL,
                reasoning_effort=settings.KG_REASONING_EFFORT,
                max_completion_tokens=settings.KG_MAX_COMPLETION_TOKENS)
    plan["plan_id"] = sha256(canonical(plan).encode()).hexdigest()
    with directory_lock(directory):
        path = directory / "plan.json"
        if path.exists():
            if json.loads(path.read_text()) != plan:
                raise ValueError("Existing KG plan differs; use a new KG_DIR instead of overwriting it")
        else:
            temporary = path.with_suffix(".tmp")
            temporary.write_text(canonical(plan), encoding="utf-8")
            temporary.replace(path)
    return dict(output=str(directory), plan_id=plan["plan_id"], papers=len(papers),
                full_text_chunks=len(chunks), maximum_first_pass_calls=len(chunks),
                model_calls=0, graph_ready=False)


def read_plan(directory, settings=None):
    from .extraction import REVISION, LIBRARY_VERSION
    plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
    content = {key: value for key, value in plan.items() if key != "plan_id"}
    if (sha256(canonical(content).encode()).hexdigest() != plan["plan_id"]
            or plan["extraction_revision"] != REVISION or plan["library_version"] != LIBRARY_VERSION):
        raise ValueError("KG plan integrity/revision mismatch; prepare a new KG_DIR")
    chunks = [SourceChunk.model_validate(chunk) for chunk in plan["chunks"]]
    identities = {(str(p["paper_id"]), str(p["build_id"]), p["collection"], p["source"])
                  for p in plan["papers"]}
    if (not chunks or len({(c.collection, c.point_id) for c in chunks}) != len(chunks)
            or any((str(c.paper_id), str(c.build_id), c.collection, c.source) not in identities
                   for c in chunks)):
        raise ValueError("KG plan has invalid chunk scope")
    if settings is not None and any(plan[field] != getattr(settings, setting) for field, setting in (
            ("model", "KG_MODEL"), ("reasoning_effort", "KG_REASONING_EFFORT"),
            ("max_completion_tokens", "KG_MAX_COMPLETION_TOKENS"))):
        raise ValueError("Extraction model/settings differ from saved plan; prepare a new KG_DIR")
    return plan, chunks


def open_checkpoints(directory, plan):
    database = sqlite3.connect(directory / "checkpoints.sqlite")
    database.row_factory = sqlite3.Row
    database.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT NOT NULL, "
                     "attempts INTEGER NOT NULL, result TEXT, error TEXT, seconds REAL, updated TEXT)")
    database.execute("CREATE TABLE IF NOT EXISTS identity (plan_id TEXT PRIMARY KEY)")
    database.execute("CREATE TABLE IF NOT EXISTS attempts (id TEXT, attempt INTEGER, status TEXT, "
                     "result TEXT, error TEXT, seconds REAL, PRIMARY KEY(id,attempt))")
    ids = [row[0] for row in database.execute("SELECT plan_id FROM identity")]
    if ids and ids != [plan["plan_id"]]:
        database.close()
        raise ValueError("Checkpoint database belongs to a different plan")
    database.execute("INSERT OR IGNORE INTO identity VALUES (?)", (plan["plan_id"],))
    for chunk in plan["chunks"]:
        database.execute("INSERT OR IGNORE INTO jobs (id,status,attempts) VALUES (?, 'pending', 0)",
                         (chunk["point_id"],))
    database.commit()
    return database


def extract(directory, settings, *, max_calls=None, retry_failed=False, failed_only=False,
            chunks_per_paper=None, component=None, tracer=None):
    """No hidden retry. Interrupted requests may have been billed: retry is explicit."""
    from .extraction import ScientificExtractor
    from .tracing import ExtractionTracing
    from src.api.core.structured import StructuredOutputError
    from openai import OpenAI
    from .selection import select_chunks
    limit = settings.KG_MAX_CALLS if max_calls is None else max_calls
    if not 1 <= limit <= 1000:
        raise ValueError("Per-invocation call limit must be 1–1000")
    client = None
    with directory_lock(directory):
        plan, chunks = read_plan(directory, settings)
        with closing(open_checkpoints(directory, plan)) as database:
            # A crashed reservation is never silently sent a second time.
            database.execute("UPDATE jobs SET status='interrupted', error='Outcome unknown; explicit retry required' "
                             "WHERE status='running'")
            database.execute("UPDATE attempts SET status='interrupted' WHERE status='running'")
            database.commit()
            states = {row["id"]: dict(row) for row in database.execute("SELECT id,status,attempts FROM jobs")}
            selected = select_chunks(chunks, states, max_calls=limit,
                chunks_per_paper=chunks_per_paper, retry_failed=retry_failed, failed_only=failed_only)
            if selected and component is None:
                if not settings.OPENAI_API_KEY.get_secret_value():
                    raise ValueError("OPENAI_API_KEY is required only for paid kg-extract")
                client = OpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value(), max_retries=0,
                                timeout=settings.KG_TIMEOUT_SECONDS)
                component = ScientificExtractor(client, settings)
            observer = tracer or ExtractionTracing(settings)

            def request(chunk):
                started = monotonic()
                with observer.generation(plan, chunk) as span:
                    try:
                        result = asyncio.run(component.run(chunk=chunk))
                        if result.batch.paper_id != chunk.paper_id or result.batch.build_id != chunk.build_id:
                            raise ValueError("Extraction batch identity mismatch")
                        result.batch.validate_sources([chunk])
                        data = result.model_dump(mode="json")
                        observer.finish(span, data, "complete", monotonic() - started)
                        return "complete", data, None, monotonic() - started
                    except Exception as error:
                        # Never save/print raw provider output, exception text or secret values.
                        usage = getattr(error, "usage", None)
                        if isinstance(error, StructuredOutputError):
                            completion = error.completion
                            token_usage = getattr(completion, "usage", None)
                            if token_usage:
                                usage = dict(input_tokens=token_usage.prompt_tokens,
                                             output_tokens=token_usage.completion_tokens,
                                             total_tokens=token_usage.total_tokens)
                        data = dict(usage=usage, usage_unknown=usage is None)
                        diagnostics = getattr(error, "safe_diagnostics", None)
                        if diagnostics is not None:
                            data["safe_diagnostics"] = diagnostics
                        for field in ("provider_model", "response_id"):
                            value = getattr(error, field, None)
                            if value is not None:
                                data[field] = value
                        observer.finish(span, data, type(error).__name__, monotonic() - started)
                        return "failed", data, type(error).__name__, monotonic() - started

            try:
                with ThreadPoolExecutor(max_workers=settings.KG_CONCURRENCY) as pool:
                    # Reserve durably immediately before each submission, not after the response.
                    futures = []
                    for chunk in selected:
                        database.execute("UPDATE jobs SET status='running',attempts=attempts+1, "
                                         "result=NULL,error=NULL,seconds=NULL WHERE id=?",
                                         (str(chunk.point_id),))
                        database.execute("INSERT INTO attempts (id,attempt,status) "
                                         "SELECT id,attempts,'running' FROM jobs WHERE id=?", (str(chunk.point_id),))
                        database.commit()
                        futures.append((chunk, pool.submit(request, chunk)))
                    for chunk, future in futures:
                        status, data, error, elapsed = future.result()
                        database.execute("UPDATE jobs SET status=?,result=?,error=?,seconds=?,updated=? WHERE id=?",
                                         (status, canonical(data), error, elapsed,
                                          datetime.now(timezone.utc).isoformat(), str(chunk.point_id)))
                        database.execute("UPDATE attempts SET status=?,result=?,error=?,seconds=? "
                                         "WHERE id=? AND attempt=(SELECT attempts FROM jobs WHERE id=?)",
                                         (status, canonical(data), error, elapsed, str(chunk.point_id), str(chunk.point_id)))
                        database.commit()
                        detail = f" ({error})" if error else ""
                        issues = data.get("safe_diagnostics", {}).get("rejection_issues", [])
                        if issues:
                            detail += ": " + "; ".join(f"{issue['code']} at {issue['path']}" for issue in issues[:3])
                        print(f"{chunk.point_id}: {status}{detail}", flush=True)
            finally:
                observer.close()
                if client:
                    client.close()
            rows = [dict(row) for row in database.execute("SELECT * FROM jobs ORDER BY id")]
            result = export(directory, plan, rows)
            attempts = [json.loads(row[0]) if row[0] else {} for row in
                        database.execute("SELECT result FROM attempts")]
            result["known_total_tokens"] = sum((entry.get("usage") or {}).get("total_tokens", 0)
                                               for entry in attempts)
            result["attempts_with_unknown_usage"] = sum(not entry.get("usage") for entry in attempts)
            result["model_calls_reserved_this_invocation"] = len(selected)
            paper_counts = {}
            for chunk in selected:
                key = str(chunk.paper_id)
                paper_counts[key] = paper_counts.get(key, 0) + 1
            result["papers_selected_this_invocation"] = [
                dict(paper_id=paper["paper_id"], title=paper["title"], chunks=paper_counts[paper["paper_id"]])
                for paper in plan["papers"] if paper["paper_id"] in paper_counts]
            return result


def export(directory, plan, rows):
    states = {status: sum(row["status"] == status for row in rows)
              for status in ("pending", "running", "complete", "failed", "interrupted")}
    candidates = dict(plan_id=plan["plan_id"], review_status="needs_review", graph_ready=False,
                      states=states, chunks=[dict(point_id=row["id"], **json.loads(row["result"]))
                                            for row in rows if row["status"] == "complete"])
    temporary = directory / "candidates.tmp"
    temporary.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(directory / "candidates.json")
    chunk_papers = {chunk["point_id"]: chunk["paper_id"] for chunk in plan["chunks"]}
    failures = dict(plan_id=plan["plan_id"], failures=[dict(
        point_id=row["id"], paper_id=chunk_papers[row["id"]], status=row["status"],
        attempts=row["attempts"], error=row["error"],
        **(json.loads(row["result"]) if row["result"] else {}),
    ) for row in rows if row["status"] in {"failed", "interrupted"}])
    for failure in failures["failures"]:
        if "safe_diagnostics" not in failure:
            failure["safe_diagnostics"] = {
                "rejection_issues": [dict(code="reason_not_recorded", path="batch")]}
    temporary = directory / "failures.tmp"
    temporary.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(directory / "failures.json")
    return dict(output=str(directory), states=states, graph_ready=False,
                candidates=str(directory / "candidates.json"),
                failures=str(directory / "failures.json"),
                total_attempts_reserved=sum(row["attempts"] for row in rows))


def validate(directory):
    """Read-only checkpoint validation; never promote review status or graph readiness."""
    with directory_lock(directory):
        plan, chunks = read_plan(directory)
        lookup = {str(chunk.point_id): chunk for chunk in chunks}
        database = sqlite3.connect(f"file:{directory.resolve() / 'checkpoints.sqlite'}?mode=ro", uri=True)
        try:
            identity = [row[0] for row in database.execute("SELECT plan_id FROM identity")]
            if identity != [plan["plan_id"]]:
                raise ValueError("Checkpoint identity does not match the plan")
            rows = list(database.execute("SELECT id,status,result FROM jobs"))
            if {row[0] for row in rows} != set(lookup):
                raise ValueError("Checkpoint chunk identities do not match the plan")
            count = 0
            for point_id, status, result in rows:
                if status == "complete":
                    batch = ExtractionBatch.model_validate(json.loads(result)["batch"])
                    if batch.paper_id != lookup[point_id].paper_id or batch.build_id != lookup[point_id].build_id:
                        raise ValueError("Checkpoint batch identity mismatch")
                    if batch.extraction_revision != plan["extraction_revision"] or batch.extraction_model != plan["model"]:
                        raise ValueError("Checkpoint model/revision mismatch")
                    batch.validate_sources([lookup[point_id]])
                    from .extraction import ScientificResult, staging_graph
                    saved = ScientificResult.model_validate(json.loads(result))
                    if saved.graph != staging_graph(batch):
                        raise ValueError("Checkpoint graph differs from its validated scientific records")
                    count += 1
            return dict(valid=True, validated_chunks=count, total_chunks=len(chunks),
                        complete=count == len(chunks), model_calls=0, graph_ready=False,
                        needs_scientific_review=True)
        finally:
            database.close()
