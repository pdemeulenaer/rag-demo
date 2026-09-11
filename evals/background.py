"""Durable background submissions and bounded polling; never retry a POST implicitly."""
from datetime import datetime, timezone
from time import monotonic, sleep

from openai import NotFoundError


class BackgroundError(ValueError):
    """Safe operator message, not a raw provider error."""


TRANSPORT = "responses-background-v1"
PENDING = {"queued", "in_progress"}
FAILED = {"failed", "incomplete", "cancelled"}
REQUEST_TIMEOUT = 20
POLL_INTERVAL = 5


def terminal_data(response):
    """Keep answer text and usage locally, not hidden reasoning or raw provider errors."""
    refused = any(part.type == "refusal" for item in response.output
                  if item.type == "message" for part in item.content)
    return {"id": response.id, "status": response.status, "model": response.model,
            "output_text": response.output_text, "refused": refused,
            "usage": response.usage.model_dump() if response.usage else None}


def validate_retry(state, retry_job):
    if retry_job is None:
        return
    entry = state.get("background_jobs", {}).get(retry_job)
    if entry is None or any(r["id"] == retry_job for r in state["results"]):
        raise BackgroundError("RETRY_JOB must name an unresolved background job, not a completed candidate/rejection.")
    if entry.get("response_id") and not entry.get("unavailable") and entry["status"] not in FAILED:
        raise BackgroundError("That background job is still retrievable; resume polling without RETRY_JOB.")


def obtain_response(client, job_id, request, state, save, *, wait_seconds=600, retry_job=None):
    jobs = state.setdefault("background_jobs", {})
    if retry_job == job_id:
        validate_retry(state, retry_job)
        state.setdefault("background_history", []).append({"job_id": job_id, **jobs.pop(job_id)})
    entry = jobs.get(job_id)
    response = None
    if entry is None:
        # A crash/disconnect before the returned ID is saved leaves an explicit
        # uncertain submission. An operator must authorize any possible duplicate.
        entry = {"transport": TRANSPORT, "status": "submitting", "response_id": None,
                 "submitted_at": datetime.now(timezone.utc).isoformat()}
        jobs[job_id] = entry
        save()
        print(f"{job_id}: submitting background request", flush=True)
        response = client.responses.create(**request, background=True, store=False, timeout=REQUEST_TIMEOUT)
        if not isinstance(response.id, str) or not response.id:
            raise BackgroundError("Submission returned no response ID; review before authorizing RETRY_JOB.")
        entry.update(response_id=response.id, status=response.status)
        save()  # The response ID must be durable before any polling begins.
    if entry.get("transport") != TRANSPORT:
        raise BackgroundError("Unsupported saved background transport; do not resubmit automatically.")
    if not entry.get("response_id"):
        raise BackgroundError(f"{job_id}: submission outcome unknown. Review API activity before using RETRY_JOB={job_id}; another submission may be billed.")
    if entry.get("unavailable"):
        raise BackgroundError(f"{job_id}: saved response is unavailable or expired. Review before using RETRY_JOB={job_id}; this would generate again.")
    if "terminal" in entry:
        result = entry["terminal"]
    else:
        deadline = monotonic() + wait_seconds
        while True:
            if response is None:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise BackgroundError(f"{job_id}: polling wait limit reached. Run the same command to resume; the remote job was not cancelled.")
                try:
                    response = client.responses.retrieve(entry["response_id"], timeout=min(REQUEST_TIMEOUT, remaining))
                except NotFoundError:
                    entry["unavailable"] = True
                    save()
                    raise BackgroundError(f"{job_id}: saved response is unavailable or expired. No new generation was submitted; review RETRY_JOB recovery in the guide.") from None
            if response.id != entry["response_id"]:
                raise BackgroundError("Background response identity mismatch; stopped without resubmitting.")
            if response.status not in PENDING | FAILED | {"completed"}:
                raise BackgroundError("Unexpected background response status; stopped without resubmitting.")
            entry["status"] = response.status
            if response.status not in PENDING:
                result = terminal_data(response)
                entry["terminal"] = result
                save()  # Retain terminal output even if local validation is interrupted.
                break
            save()
            print(f"{job_id}: {response.status} (background)", flush=True)
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise BackgroundError(f"{job_id}: polling wait limit reached. Run the same command to resume; the remote job was not cancelled.")
            sleep(min(POLL_INTERVAL, remaining))
            response = None
    if result["status"] != "completed":
        raise BackgroundError(f"{job_id}: background response {result['status']}. No automatic regeneration. Review before using RETRY_JOB={job_id}.")
    return result
