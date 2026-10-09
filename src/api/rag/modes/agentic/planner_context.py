"""Read-only, deterministic planner previews when the next call exceeds its budget.

Keep the native tool-call/result protocol and evidence identifiers. Full artifacts
and the graph's evidence remain authoritative for final generation.
"""
from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from src.api.rag.modes.agentic.policies import focused_requirement_text


RECOVERY_TEXT_CHARS = 6000
RECOVERY_CHUNK_CHARS = 400
_STOPWORDS = {"the", "and", "from", "with", "that", "this", "what", "which", "report",
              "paper", "reported", "include", "about", "could", "used", "into", "its"}


def _excerpt(text: str, query: str, limit: int) -> tuple[str, int]:
    terms = set(re.findall(r"\w{3,}", query.casefold())) - _STOPWORDS
    positions = [match.start() for match in re.finditer(r"\w{3,}", text)
                 if match.group().casefold() in terms]
    starts = {max(0, min(position - limit // 3, len(text) - limit)) for position in positions}
    start = max(starts, key=lambda offset: (
        len(terms & set(re.findall(r"\w{3,}", text[offset:offset + limit].casefold()))), -offset,
    )) if starts else 0
    return text[start:start + limit], start


def frozen_planner_messages(messages, requirements, parameter_effects=()):
    """Replace the completed definition pair once, before later planner calls.

    No summarizing model, altered question, orphan tool response or evidence loss.
    """
    definition_ids = {call["id"] for message in messages if isinstance(message, AIMessage)
                      and len(message.tool_calls) == 1 for call in message.tool_calls
                      if call["name"] == "define_requirements"}
    completed = {message.tool_call_id for message in messages if isinstance(message, ToolMessage)
                 and message.name == "define_requirements" and message.status != "error"}
    removable = definition_ids & completed
    result = list(messages)
    if removable:
        result = [message for message in result if not (
            isinstance(message, AIMessage) and any(call["id"] in removable for call in message.tool_calls)
            or isinstance(message, ToolMessage) and message.tool_call_id in removable)]
        result.insert(1, SystemMessage(content="Requirements already defined. Do not redefine. "
            "Frozen retrieval navigation (not extra user requests): "
            + json.dumps({"requirements": [row.model_dump() for row in requirements],
                          "parameter_effects": [row.model_dump() for row in parameter_effects]},
                         ensure_ascii=False)))
    return result


def compact_planner_messages(messages, requirements, parameter_effects=()):
    """Shorten tool text only, preserving original question, needs and call/result IDs."""
    calls = {call["id"]: call for message in messages if isinstance(message, AIMessage)
             for call in message.tool_calls}
    descriptions = {row.id: focused_requirement_text(row.description) for row in requirements}
    result = list(messages)
    remaining, seen = RECOVERY_TEXT_CHARS, set()
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, ToolMessage) or message.name not in {
            "search_chunks", "get_neighbors", "get_section", "search_papers",
        }:
            continue
        try:
            payload = json.loads(message.content)
        except (ValueError, TypeError):
            continue  # Preserve error/protocol messages; never guess their structure.
        if not isinstance(payload, dict) or not isinstance(payload.get("evidence"), list):
            continue
        args = calls.get(message.tool_call_id, {}).get("args") or {}
        query = args.get("query") or descriptions.get(args.get("need_id"), "")
        payload["paper_catalog"] = {row.get("build_id"): {
            "paper_id": row.get("paper_id"), "title": row.get("title")}
            for row in payload["evidence"] if row.get("build_id")}
        for row in payload["evidence"]:
            text = str(row.get("text") or "")
            key = (row.get("build_id"), row.get("id"))
            duplicate = key in seen
            if duplicate:
                excerpt, start = "", 0
            else:
                excerpt, start = _excerpt(text, query, min(remaining, RECOVERY_CHUNK_CHARS))
                remaining -= len(excerpt)
                seen.add(key)
            row.update(text=excerpt, excerpt_start=start,
                       text_truncated=bool(row.get("text_truncated")) or len(excerpt) < len(text))
            if duplicate:
                row["text_omitted_reason"] = "duplicate_chunk_in_later_result"
            # Preserve navigable identities and scientific section/page context;
            # repeated full titles/empty vector-search metadata are not new evidence.
            for name in tuple(row):
                if name not in {"id", "build_id", "paper_id", "page", "section_header",
                                "chunk_index", "text", "text_chars", "text_truncated",
                                "excerpt_start", "text_omitted_reason"}:
                    del row[name]
        for paper in payload.get("papers", []):
            paper["abstract"] = str(paper.get("abstract") or "")[:200]
        payload.update(text_mode="compacted_preview", planner_context_compacted=True,
                       recovery_hint="Hidden text is not absent evidence. Read an exact observed "
                       "anchor if needed; search missing facts with concise paper-filtered queries.")
        result[index] = message.model_copy(update={
            "content": json.dumps(payload, ensure_ascii=False), "artifact": None,
        })
    # The completed definition pair repeats descriptions, search text and schemas.
    # Replace BOTH sides together, never leave an orphan native tool response.
    # Keep all retrieval/error/terminal pairs so recent recovery feedback survives.
    return frozen_planner_messages(result, requirements, parameter_effects)
