from dataclasses import replace
from unittest.mock import Mock

import pytest

from src.api.papers.extraction import chunk_pages, extract_document, token_count, SPEC
from src.api.papers.reindex import preview, select_replacements
from tests.unit.test_papers import catalogue, settings, paper, pdf_bytes


def test_pages_sections_and_blank_page_numbers():
    pages = [{"page_number": 1, "text": "# Results\n\nFirst paragraph."},
             {"page_number": 2, "text": ""},
             {"page_number": 3, "text": "Continued result.\n\n## Masses\n\nCluster masses."}]
    chunks = chunk_pages(pages)
    assert [c["page_number"] for c in chunks] == [1, 3, 3]
    assert [c["section_header"] for c in chunks] == ["Results", "Results", "Results > Masses"]
    assert all(c["token_count"] == token_count(c["text"]) for c in chunks)


def test_table_rows_headers_and_prose_are_separate():
    rows = [f"| cluster-{i} | {i * 100} solar masses |" for i in range(20)]
    header = "| Cluster | Mass |\n| --- | --- |"
    text = "# Results\n\nIntro.\n" + header + "\n" + "\n".join(rows) + "\nConclusion."
    chunks = chunk_pages([{"page_number": 4, "text": text}], max_tokens=64, overlap_tokens=8)
    tables = [c for c in chunks if c["content_kind"] == "table"]
    assert len(tables) > 1
    assert all(c["text"].startswith(header) for c in tables)
    assert [row for c in tables for row in c["text"].splitlines()[2:]] == rows
    assert chunks[-1]["text"] == "Conclusion."
    assert all(c["token_count"] <= 64 for c in chunks)


def test_wide_table_rows_become_explicit_unstructured_evidence():
    text = "| A | B |\n| --- | --- |\n| " + "value " * 100 + " | B |"
    chunks = chunk_pages([{"page_number": 1, "text": text}], max_tokens=32, overlap_tokens=4)
    assert all(chunk["content_kind"] == "table_unstructured" for chunk in chunks)
    assert all(chunk["token_count"] <= 32 for chunk in chunks)


def test_malformed_wide_table_header_becomes_explicit_unstructured_evidence():
    text = "| Caption<br>" + "value " * 100 + "|\n| --- |\n| data |"
    chunks = chunk_pages([{"page_number": 1, "text": text}], max_tokens=32, overlap_tokens=4)
    assert all(chunk["content_kind"] == "table_unstructured" for chunk in chunks)
    assert all(chunk["token_count"] <= 32 for chunk in chunks)
    assert "Caption" in chunks[0]["text"]


def test_adjacent_tables_do_not_merge_headers():
    first = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    second = "| C | D |\n| --- | --- |\n| 3 | 4 |"
    chunks = chunk_pages([{"page_number": 1, "text": first + "\n\n" + second}])
    assert [c["text"] for c in chunks] == [first, second]


def test_long_unicode_prose_preserved_and_token_bounded():
    original = "星団µ⊙🌟" * 200
    chunks = chunk_pages([{"page_number": 1, "text": original}], max_tokens=32, overlap_tokens=0)
    assert "".join(c["text"] for c in chunks) == original
    assert all(c["token_count"] <= 32 for c in chunks)
    with pytest.raises(ValueError, match="chunk budget"):
        chunk_pages([{"page_number": 1, "text": original}], max_chunks=1)


def test_control_token_like_text_is_ordinary_evidence():
    assert chunk_pages([{"page_number": 1, "text": "<|endoftext|>"}])[0]["text"] == "<|endoftext|>"


def test_real_pdf_extraction_and_blank_pages():
    import pymupdf
    with pymupdf.open() as doc:
        doc.new_page()
        page = doc.new_page()
        page.insert_text((50, 100), "A globular cluster has many stars.")
        data = doc.tobytes()
    pages, chunks = extract_document(data)
    assert len(pages) == 2
    assert all(c["page_number"] == 2 for c in chunks)
    assert "globular cluster" in chunks[0]["text"]


def test_ocr_explicitly_disabled(monkeypatch):
    import pymupdf4llm
    mock = Mock(return_value=[{"text": "# Results\n\nStars."}])
    monkeypatch.setattr(pymupdf4llm, "to_markdown", mock)
    extract_document(pdf_bytes())
    assert mock.call_args.kwargs["use_ocr"] is False
    assert mock.call_args.kwargs["page_chunks"] is True
    assert mock.call_args.kwargs["write_images"] is False


def old_build(catalogue, settings, paper):
    from types import SimpleNamespace
    old_settings = SimpleNamespace(pipeline_id="plain-text-v1", PAPERS_COLLECTION=settings.PAPERS_COLLECTION,
                                   EMBEDDING_MODEL=settings.EMBEDDING_MODEL)
    identifier = catalogue.discover(paper, old_settings)
    old = catalogue.get_build(identifier)
    catalogue.activate(old, {"chunk_count": 1})
    return old


def test_reindex_preview_and_queue_idempotent(catalogue, settings, paper):
    old = old_build(catalogue, settings, paper)
    before = catalogue.all_builds()
    rows = preview(catalogue, settings)
    assert len(rows) == 1 and rows[0]["status"] == "not_queued"
    assert catalogue.all_builds() == before
    new = select_replacements(catalogue, settings, 10)[0]
    assert new["id"] != old["id"]
    assert new["paper_id"] == old["paper_id"]
    assert catalogue.active(settings)[0]["id"] == old["id"]
    assert select_replacements(catalogue, settings, 10)[0]["id"] == new["id"]
    catalogue.start(new["id"])
    catalogue.fail(new["id"], "fixture")
    assert catalogue.active(settings)[0]["id"] == old["id"]
    catalogue.activate(new, {"chunk_count": 1})
    assert preview(catalogue, settings) == []
    assert select_replacements(catalogue, settings, 10) == []


def test_reindex_excludes_backlog_and_respects_limit(catalogue, settings, paper):
    old_build(catalogue, settings, paper)
    old_build(catalogue, settings, replace(paper, arxiv_id="2609.00002"))
    backlog = catalogue.discover(replace(paper, arxiv_id="2609.00003"), settings)
    selected = select_replacements(catalogue, settings, 1)
    assert len(selected) == 1
    assert selected[0]["id"] != backlog
    assert len(preview(catalogue, settings)) == 2


def test_reindex_honors_attempt_budget_and_tombstones(catalogue, settings, paper):
    old_build(catalogue, settings, paper)
    new = select_replacements(catalogue, settings, 1)[0]
    catalogue.update_build(new["id"], attempts=settings.ARXIV_MAX_ATTEMPTS, status="failed")
    assert preview(catalogue, settings)[0]["blocked"]
    assert select_replacements(catalogue, settings, 1) == []
    catalogue.tombstone(paper.arxiv_id)
    assert preview(catalogue, settings) == []


def test_pipeline_identity_includes_extraction(settings, monkeypatch):
    original = settings.pipeline_id
    monkeypatch.setitem(SPEC, "version", "future-extractor")
    assert settings.pipeline_id != original


def test_upload_same_bytes_upgrade_but_current_build_deduplicates(catalogue, tmp_path, monkeypatch):
    import sys
    from hashlib import sha256
    from types import SimpleNamespace
    from src.api.papers.uploads import register_upload
    path = tmp_path / "paper.pdf"
    path.write_bytes(pdf_bytes())
    prompt = tmp_path / "prompt.yml"
    prompt.write_text("fixture")
    config = SimpleNamespace(QDRANT_COLLECTION_NAME="uploads", EMBEDDING_MODEL="test-model",
                             IMAGE_DESCRIPTION_MODEL="test-image", SUMMARIZATION_MODEL="test-summary",
                             IMAGE_DESCRIPTION_PROMPT_TEMPLATE_PATH=str(prompt))
    monkeypatch.setitem(sys.modules, "src.api.core.config", SimpleNamespace(config=config))
    digest = sha256(path.read_bytes()).hexdigest()
    old = catalogue.upload(digest, {"title": "paper.pdf", "file_name": "paper.pdf", "file_hash": digest},
                           "uploads", "test-model", "legacy-upload-v2")
    catalogue.activate(old, {"chunk_count": 1})
    new = register_upload(catalogue, path, "sync")
    assert old["paper_id"] == new["paper_id"] and old["id"] != new["id"]
    assert catalogue.inventory("uploads")[0]["active_build"] == old["id"]
    catalogue.activate(new, {"chunk_count": 1})
    assert register_upload(catalogue, path, "sync")["id"] == new["id"]
    assert register_upload(catalogue, path, "batch")["id"] == new["id"]
    assert len(catalogue.all_builds()) == 2
