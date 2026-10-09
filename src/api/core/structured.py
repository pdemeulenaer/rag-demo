"""Native OpenAI Pydantic parsing, one request at a time, without schema rewrites.

Callers own retry/repair budgets. This module only normalizes safe failure metadata;
it does not validate scientific claims or decide whether to retry.
"""
from openai import ContentFilterFinishReasonError, LengthFinishReasonError
from pydantic import ValidationError


class StructuredOutputError(RuntimeError):
    """No typed output, without exposing provider text or validation input."""

    code = "invalid_structured_response"

    def __init__(self, safe_diagnostics, completion=None):
        super().__init__("Provider returned invalid structured output.")
        self.safe_diagnostics = safe_diagnostics
        self.completion = completion


def _failure(code, completion=None, error=None):
    issues = error.errors(include_input=False) if isinstance(error, ValidationError) else []
    choices = getattr(completion, "choices", None) or []
    choice = choices[0] if choices else None
    message = getattr(choice, "message", None)
    usage = getattr(completion, "usage", None)
    content = getattr(message, "content", None)
    details = {
        "validation_error_codes": sorted({str(row["type"]) for row in issues})[:10] or [code],
        "validation_error_locations": sorted({
            ".".join(str(part) for part in row.get("loc", ()))[:128] for row in issues
        })[:10],
        "provider_finish_reason": str(getattr(choice, "finish_reason", None) or
                                      getattr(completion, "status", None) or "unknown")[:32],
        "provider_completion_tokens": getattr(usage, "completion_tokens", None)
                                      if choices else getattr(usage, "output_tokens", None),
        "provider_content_chars": len(content) if isinstance(content, str) else None,
        "provider_refusal": bool(getattr(message, "refusal", None)),
    }
    return StructuredOutputError(details, completion)


def parse_chat(client, response_model, **request):
    """Use the SDK's schema converter and parser; no local/provider retries here."""
    try:
        raw = client.chat.completions.parse(response_format=response_model, **request)
    except ValidationError as error:
        raise _failure("invalid_structured_response", error=error) from error
    except LengthFinishReasonError as error:
        raise _failure("completion_limit", error.completion) from error
    except ContentFilterFinishReasonError as error:
        raise _failure("content_filter") from error
    message = raw.choices[0].message if raw.choices else None
    parsed = getattr(message, "parsed", None)
    if parsed is None:
        raise _failure("provider_refusal" if getattr(message, "refusal", None)
                       else "missing_parsed_output", raw)
    return parsed, raw


def parse_response(client, response_model, **request):
    """Synchronous Responses API parsing only; background jobs keep their lifecycle."""
    try:
        raw = client.responses.parse(text_format=response_model, **request)
    except ValidationError as error:
        raise _failure("invalid_structured_response", error=error) from error
    parsed = raw.output_parsed
    if parsed is None or raw.status != "completed":
        refusal = any(getattr(content, "type", None) == "refusal"
                      for item in raw.output for content in (getattr(item, "content", None) or []))
        error = _failure("provider_refusal" if refusal else
                         "incomplete_output" if raw.status == "incomplete" else "missing_parsed_output", raw)
        error.safe_diagnostics["provider_refusal"] = refusal
        raise error
    return parsed, raw
