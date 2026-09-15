"""PDF -> page-aware Markdown -> structure-aware text chunks (no model calls).

Keep this module independent of API settings and figure/metadata generation.
Changes to extraction, cleanup or splitting semantics require a SPEC version bump.
"""
from functools import lru_cache
import os
from pathlib import Path
import re
import sys


SPEC = {"version": "markdown-structure-v1", "pymupdf": "1.27.2.3",
        "pymupdf4llm": "1.27.2.3", "ocr": False,
        "tokenizer": "cl100k_base", "max_tokens": 512, "overlap_tokens": 64}
HEADER = re.compile(r"^(#{1,6})\s+(.+)$")
TABLE_SEPARATOR = re.compile(r"^\s*\|?(?:\s*:?-{2,}:?\s*\|)+\s*$")


@lru_cache(maxsize=1)
def encoder():
    import tiktoken
    # Cache alongside the environment so Docker's copied venv includes the data.
    os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(Path(sys.prefix) / "tokenizer-cache"))
    return tiktoken.get_encoding(SPEC["tokenizer"])


def token_count(text):
    # Paper content may contain strings resembling tokenizer control tokens.
    return len(encoder().encode(text, disallowed_special=()))


def extract_pages(pdf):
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    import pymupdf
    import pymupdf4llm
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        if document.is_encrypted:
            raise ValueError("Encrypted PDF is not supported")
        pages = pymupdf4llm.to_markdown(document, page_chunks=True, use_ocr=False,
                                      write_images=False, show_progress=False)
        if len(pages) != len(document):
            raise ValueError("Extractor returned an incomplete page list")
        # Preserve blank pages and original PDF numbering in the saved artifact.
        result = [{"page_number": n, "text": (page.get("text") or "").strip()}
                  for n, page in enumerate(pages, 1)]
    if not any(page["text"] for page in result):
        raise ValueError("PDF has no extractable text; OCR is disabled")
    return result


def markdown_document(pages):
    return "\n\n".join(f"<!-- page {p['page_number']} -->\n\n{p['text']}" for p in pages)


def _sections(text, stack):
    lines = []
    for line in text.splitlines():
        match = HEADER.match(line)
        if match:
            if lines:
                yield " > ".join(title for _, title in stack), "\n".join(lines)
            level, title = len(match[1]), match[2].strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            lines = [line]
        else:
            lines.append(line)
    if lines:
        yield " > ".join(title for _, title in stack), "\n".join(lines)


def _prose_parts(text, cap):
    """Prefer natural boundaries; character fallback never cuts UTF-8 tokens."""
    while text:
        if token_count(text) <= cap:
            yield text
            return
        low, high = 1, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if token_count(text[:middle]) <= cap:
                low = middle
            else:
                high = middle - 1
        cut = low
        # Prefer a sentence, line or word boundary in the latter half of the window.
        for pattern in (r"(?<=[.!?])\s+", r"\n", r"\s+"):
            boundaries = list(re.finditer(pattern, text[:cut]))
            if boundaries and boundaries[-1].start() >= cut // 2:
                cut = boundaries[-1].end()
                break
        part = text[:cut].strip()
        if not part or token_count(part) > cap:
            raise ValueError("Cannot split prose within token budget")
        yield part
        text = text[cut:].strip()


def _table_parts(block, cap):
    """Preserve complete rows and repeat headers; never silently shred a wide row."""
    lines = block.splitlines()
    if len(lines) < 2 or not TABLE_SEPARATOR.match(lines[1]):
        if token_count(block) > cap:
            raise ValueError("Oversized table without a recognizable header; review extraction")
        yield block
        return
    header = "\n".join(lines[:2])
    current = header
    if token_count(header) > cap:
        raise ValueError("Table header exceeds token budget; review extraction")
    for row in lines[2:]:
        if token_count(header + "\n" + row) > cap:
            raise ValueError("Table row exceeds token budget; review extraction")
        if token_count(current + "\n" + row) > cap:
            yield current
            current = header
        current += "\n" + row
    yield current


def _unstructured_table_parts(block, cap):
    """Keep malformed wide tables searchable without claiming their rows survived.

    Some journal PDFs are emitted as a single giant Markdown header cell or
    row with ``<br>`` separators. There is no faithful table-row split to
    preserve in that representation, but rejecting the entire paper is worse
    than storing its evidence explicitly as unstructured table text.
    """
    yield from _prose_parts(block.replace("<br>", "\n"), cap)


def _blocks(body):
    lines, table = [], False
    for line in body.splitlines():
        is_table = line.lstrip().startswith("|")
        if not line.strip() or (lines and is_table != table):
            if lines:
                yield table, "\n".join(lines)
            lines = []
        if line.strip():
            table = is_table
            lines.append(line.strip() if table else line)
    if lines:
        yield table, "\n".join(lines)


def chunk_pages(pages, max_chunks=1000, *, max_tokens=512, overlap_tokens=64):
    if max_tokens < 16 or not 0 <= overlap_tokens < max_tokens or max_chunks < 1:
        raise ValueError("Invalid chunk budget")
    chunks, stack = [], []

    def emit(text, page, section, kind):
        if text.strip():
            count = token_count(text)
            if count > max_tokens:
                raise ValueError("Chunk exceeds token budget")
            chunks.append({"page_number": page, "section_header": section,
                           "text": text, "token_count": count, "content_kind": kind})
            if len(chunks) > max_chunks:
                raise ValueError("Paper exceeds configured chunk budget")

    for page in pages:
        for section, body in _sections(page["text"], stack):
            pending = []
            for table, block in _blocks(body.strip()):
                if table:
                    emit("\n\n".join(pending), page["page_number"], section, "text")
                    pending = []
                    try:
                        for part in _table_parts(block, max_tokens):
                            emit(part, page["page_number"], section, "table")
                    except ValueError:
                        # The table cannot fit while retaining complete rows.
                        # Preserve the source as evidence, but mark that its
                        # tabular structure was not safely retained.
                        for part in _unstructured_table_parts(block, max_tokens):
                            emit(part, page["page_number"], section, "table_unstructured")
                    continue
                for part in _prose_parts(block, max_tokens):
                    combined = "\n\n".join([*pending, part])
                    if pending and token_count(combined) > max_tokens:
                        emit("\n\n".join(pending), page["page_number"], section, "text")
                        tail = []
                        for previous in reversed(pending):
                            trial = [previous, *tail]
                            if token_count("\n\n".join(trial)) > overlap_tokens:
                                break
                            tail = trial
                        pending = tail if token_count("\n\n".join([*tail, part])) <= max_tokens else []
                    pending.append(part)
            emit("\n\n".join(pending), page["page_number"], section, "text")
    if not chunks:
        raise ValueError("PDF has no extractable text; OCR is disabled")
    return chunks


def extract_document(pdf, max_chunks=1000):
    pages = extract_pages(pdf)
    return pages, chunk_pages(pages, max_chunks, max_tokens=SPEC["max_tokens"],
                              overlap_tokens=SPEC["overlap_tokens"])


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New local inspection directory; never overwritten")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new directory")
    pages, chunks = extract_document(args.pdf.read_bytes())
    args.output.mkdir(parents=True, mode=0o700, exist_ok=False)
    from .artifacts import ArtifactStore
    from types import SimpleNamespace
    store = ArtifactStore(SimpleNamespace(PAPERS_STORAGE_MODE="LOCAL", PAPERS_ARTIFACT_DIR=args.output))
    store.put("preview", "document.md", markdown_document(pages).encode())
    store.put_json("preview", "pages.json", pages)
    store.put_json("preview", "chunks.json", chunks)
    store.put_json("preview", "extraction.json", SPEC)
    print(json.dumps({"pages": len(pages), "chunks": len(chunks),
                      "table_chunks": sum(c["content_kind"] == "table" for c in chunks),
                      "output": str(args.output), "model_calls": 0}))


if __name__ == "__main__":
    main()
