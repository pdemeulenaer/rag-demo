"""Deterministic citation windows inside an existing chunk; not retrieval rechunking."""
from pydantic import Field

from .contracts import Record, Text


SPAN_SPEC = {"version": "source-spans-v1", "target_characters": 360,
             "boundaries": "paragraph_then_whitespace", "offset_unit": "unicode_codepoint"}


class SourceSpan(Record):
    id: Text
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str


def source_spans(text: str) -> list[SourceSpan]:
    """Select exact substrings, preserving math, Markdown and Unicode unchanged.

    Offsets are Python string indices, end-exclusive. Whitespace between windows
    need not be quoted; every non-whitespace source character is covered once.
    IDs are local to this one chunk and must never resolve against another chunk.
    """
    result = []
    cursor = 0
    while cursor < len(text):
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor == len(text):
            break
        target = min(cursor + SPAN_SPEC["target_characters"], len(text))
        paragraph = text.find("\n\n", cursor, target)
        if paragraph >= 0:
            end = paragraph
        elif target < len(text):
            # Never cut a long formula/token just to satisfy the preferred length.
            boundary = next((i for i in range(target, cursor, -1) if text[i].isspace()), None)
            if boundary is None:
                boundary = next((i for i in range(target, len(text)) if text[i].isspace()), len(text))
            end = boundary
        else:
            end = len(text)
        while end > cursor and text[end - 1].isspace():
            end -= 1
        result.append(SourceSpan(id=f"s{len(result) + 1:03d}", start=cursor, end=end, text=text[cursor:end]))
        cursor = end
    return result
