"""Optional best-effort Langfuse generations without importing global API config."""
from contextlib import contextmanager
import warnings


class ExtractionTracing:
    def __init__(self, settings):
        self.client = None
        if settings.LANGFUSE_ENABLED:
            try:
                from langfuse import Langfuse
                self.client = Langfuse(public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY.get_secret_value(),
                    base_url=settings.LANGFUSE_BASE_URL)
            except Exception:
                warnings.warn("KG Langfuse unavailable; local checkpoints remain authoritative")

    @contextmanager
    def generation(self, plan, chunk):
        span = None
        if self.client:
            try:
                span = self.client.start_observation(name="kg.extract", as_type="generation",
                    model=plan["model"], input={"source_text": chunk.text},
                    metadata={"plan_id": plan["plan_id"], "build_id": str(chunk.build_id),
                              "point_id": str(chunk.point_id), "extraction_revision": plan["extraction_revision"]})
            except Exception:
                warnings.warn("KG trace could not be started")
        try:
            yield span
        finally:
            if span:
                try:
                    span.end()
                except Exception:
                    warnings.warn("KG trace could not be ended")

    def finish(self, span, data, status, seconds):
        if span:
            try:
                span.update(output=data.get("batch"), usage_details=data.get("usage"),
                            metadata={"status": status, "elapsed_seconds": seconds,
                                      "usage_unknown": data.get("usage") is None,
                                      "provider_model": data.get("provider_model"),
                                      "response_id": data.get("response_id")})
            except Exception:
                warnings.warn("KG trace could not be updated")

    def close(self):
        if self.client:
            try:
                self.client.flush()
                self.client.shutdown()
            except Exception:
                warnings.warn("KG traces could not be flushed")
