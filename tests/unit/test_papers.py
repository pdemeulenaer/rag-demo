from dataclasses import replace
from contextlib import closing
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from qdrant_client import QdrantClient, models as m

from src.api.papers.arxiv import ArxivClient, Paper, matches_scope, parse_atom
from src.api.papers.artifacts import ArtifactStore
from src.api.papers.catalogue import Catalogue, snapshot_id
from src.api.papers.ingestion import PaperIndexer, discover_daily, extract_chunks, process_pending
from src.api.papers.settings import PaperSettings
from src.api.rag.search import search_points


@pytest.fixture
def settings(tmp_path):
    return PaperSettings(_env_file=None, PAPERS_DATABASE_URL="sqlite://",
                         PAPERS_ARTIFACT_DIR=tmp_path, PAPERS_STORAGE_MODE="LOCAL")


@pytest.fixture
def catalogue(settings):
    catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
    catalogue.initialize()
    yield catalogue
    catalogue.close()


@pytest.fixture
def paper():
    return Paper("2609.00001", 1, "Ages of globular clusters", "Stellar populations",
                 ["A. Author"], ["astro-ph.GA"], "2026-09-01T00:00:00Z", "2026-09-01T00:00:00Z")


def pdf_bytes():
    import pymupdf
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((40, 40), "Globular clusters constrain stellar evolution.")
        return doc.tobytes()


@pytest.mark.parametrize("categories,title,expected", [
    (["astro-ph.GA"], "Globular clusters in M31", True),
    (["astro-ph.SR", "astro-ph.GA"], "Young massive clusters", True),
    (["astro-ph.GA"], "Star-cluster ages", True),
    (["astro-ph.SR"], "Globular cluster ages", False),
    (["astro-ph.GA"], "Galaxy clusters and dark matter", False),
    (["astro-ph.GA"], "The cluster NGC 104", False),
    (["astro-ph.GA"], "Nonstellar clustering", False),
])
def test_scope(settings, categories, title, expected):
    assert matches_scope(categories, title, "", settings) is expected


def test_abstract_and_empty_topic_filter(settings):
    assert matches_scope(["astro-ph.GA"], "M31", "An open cluster survey", settings)
    settings.ARXIV_TOPIC_TERMS = ""
    assert matches_scope(["astro-ph.GA"], "Galaxy dynamics", "", settings)
    assert not matches_scope(["astro-ph.SR"], "Star cluster", "", settings)


def atom(identifier="2609.00001v2"):
    return f'''<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
      <opensearch:totalResults>1</opensearch:totalResults><entry>
      <id>http://arxiv.org/abs/{identifier}</id><title>Star clusters</title>
      <summary>Open cluster ages</summary><author><name>A. Author</name></author>
      <category term="astro-ph.GA"/><published>2026-09-01T00:00:00Z</published>
      <updated>2026-09-03T00:00:00Z</updated></entry></feed>'''


def test_atom_versioned_identity():
    papers, total = parse_atom(atom())
    assert total == 1
    assert papers[0].arxiv_id == "2609.00001"
    assert papers[0].version == 2
    assert papers[0].pdf_url.endswith("2609.00001v2")
    assert parse_atom(atom("astro-ph/0601001v1"))[0][0].arxiv_id == "astro-ph/0601001"
    with pytest.raises(ValueError):
        parse_atom(atom("2609.00001"))


def test_retry_and_serial_pacing():
    sleeps = []
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(503, headers={"Retry-After": "5"}) if len(calls) == 1 else httpx.Response(200, text=atom())
    client = ArxivClient("test", httpx.Client(transport=httpx.MockTransport(respond)),
                         sleep=sleeps.append, clock=lambda: 0)
    assert parse_atom(client.get("https://export.arxiv.org/api/query"))[0]
    assert sleeps == [5, 3.1]
    client.close()


def test_download_redirect_and_size_limits(paper):
    client = ArxivClient("test", httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(302, headers={"Location": "http://127.0.0.1/secrets"}))), sleep=lambda _: None)
    with pytest.raises(ValueError, match="redirect host"):
        client.download_pdf(paper, 100)
    client.close()
    client = ArxivClient("test", httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=b"%PDF-" + b"x" * 100))), sleep=lambda _: None)
    with pytest.raises(ValueError, match="size limit"):
        client.download_pdf(paper, 30)
    client.close()


def test_discovery_is_idempotent(catalogue, settings, paper):
    first = catalogue.discover(paper, settings)
    assert catalogue.discover(paper, settings) == first
    assert len(catalogue.status()) == 1
    assert catalogue.active(settings) == []
    assert len(catalogue.pending(settings, 10)) == 1


def test_activation_failure_and_old_version_retry(catalogue, settings, paper):
    catalogue.discover(paper, settings)
    first = catalogue.pending(settings, 10)[0]
    catalogue.activate(first, {"chunk_count": 1})
    fingerprint = snapshot_id(catalogue.active(settings))
    second_id = catalogue.discover(replace(paper, version=2), settings)
    second = catalogue.pending(settings, 10)[0]
    catalogue.start(second_id)
    catalogue.fail(second_id, "test")
    assert snapshot_id(catalogue.active(settings)) == fingerprint
    catalogue.activate(second, {"chunk_count": 1})
    catalogue.activate(first, {"chunk_count": 1})
    assert catalogue.active(settings)[0]["version"] == 2
    catalogue.tombstone(paper.arxiv_id)
    assert catalogue.active(settings) == []


def test_daily_checkpoint_and_backlog(catalogue, settings, paper):
    client = Mock()
    client.oai_sets.return_value = {"astro-ph.GA": "physics:astro-ph:GA"}
    record = {"id": paper.arxiv_id, "deleted": False, "title": paper.title,
              "abstract": paper.abstract, "categories": paper.categories, "license": "cc-by"}
    client.changes.return_value = iter([("2026-09-09T00:00:00Z", [record]),
                                       ("2026-09-09T00:10:00Z", [])])
    client.resolve.return_value = [paper]
    assert discover_daily(client, catalogue, settings) == 1
    key = f"oai:{settings.scope_id}:astro-ph.GA"
    assert catalogue.checkpoint(key) == "2026-09-09T00:00:00Z"
    assert catalogue.pending(settings, 1)[0]["metadata"]["license"] == "cc-by"
    def broken_pages():
        yield "2026-09-10T00:00:00Z", [record]
        raise RuntimeError("pagination interrupted")
    client.changes.return_value = broken_pages()
    with pytest.raises(RuntimeError):
        discover_daily(client, catalogue, settings)
    assert catalogue.checkpoint(key) == "2026-09-09T00:00:00Z"
    assert len(catalogue.status()) == 1


def test_oai_parser_and_resumption_tokens():
    requests = []
    def response(request):
        requests.append(dict(request.url.params))
        if len(requests) == 1:
            body = '''<record><header><identifier>oai:arXiv.org:2609.00001</identifier></header>
            <metadata><arXiv xmlns="http://arxiv.org/OAI/arXiv/"><title>Star clusters</title>
            <abstract>Ages</abstract><categories>astro-ph.SR astro-ph.GA</categories>
            <license>cc-by</license></arXiv></metadata></record><resumptionToken>next</resumptionToken>'''
        else:
            body = '<record><header status="deleted"><identifier>oai:arXiv.org:2609.00002</identifier></header></record>'
        return httpx.Response(200, text=f'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><responseDate>2026-09-09T00:00:00Z</responseDate><ListRecords>{body}</ListRecords></OAI-PMH>')
    client = ArxivClient("test", httpx.Client(transport=httpx.MockTransport(response)), sleep=lambda _: None)
    pages = list(client.changes("physics:astro-ph:GA", "2026-09-01"))
    assert pages[0][1][0]["categories"] == ["astro-ph.SR", "astro-ph.GA"]
    assert pages[1][1][0] == {"id": "2609.00002", "deleted": True}
    assert requests[1] == {"verb": "ListRecords", "resumptionToken": "next"}
    client.close()


def test_process_with_local_qdrant(catalogue, settings, paper):
    catalogue.discover(paper, settings)
    client = Mock()
    client.download_pdf.return_value = pdf_bytes()
    with closing(QdrantClient(":memory:")) as qdrant:
        indexer = PaperIndexer(settings, qdrant, lambda texts: [[1., 0., 0.] for _ in texts])
        result = process_pending(client, catalogue, settings, ArtifactStore(settings), indexer, 1)
        assert result == {"completed": 1, "failed": 0}
        active = catalogue.active(settings)
        assert active[0]["manifest"]["chunk_count"] == 1
        assert active[0]["manifest"]["source"]["sha256"]
        assert active[0]["manifest"]["markdown"]["sha256"]
        assert active[0]["manifest"]["pages"]["sha256"]
        assert active[0]["manifest"]["extraction"]["version"] == "markdown-structure-v1"
        scope = m.Filter(must=[m.FieldCondition(key="build_id", match=m.MatchAny(any=[active[0]["id"]]))])
        for mode in ["vanilla", "hybrid"]:
            points = search_points(qdrant, settings.PAPERS_COLLECTION, [1., 0., 0.], "globular", 5, mode, scope).points
            assert len(points) == 1
            assert points[0].payload["page_number"] == 1
            assert points[0].payload["paper_version"] == 1
        assert process_pending(client, catalogue, settings, ArtifactStore(settings), indexer, 1)["completed"] == 0


def test_processing_limit_and_failed_index(catalogue, settings, paper):
    catalogue.discover(paper, settings)
    catalogue.discover(replace(paper, arxiv_id="2609.00002"), settings)
    client, indexer = Mock(), Mock()
    client.download_pdf.return_value = pdf_bytes()
    indexer.index.side_effect = RuntimeError("index unavailable")
    assert process_pending(client, catalogue, settings, ArtifactStore(settings), indexer, 1) == {"completed": 0, "failed": 1}
    assert catalogue.active(settings) == []
    assert len(catalogue.pending(settings, 10)) == 2
    assert sum(b["attempts"] for b in catalogue.status()) == 1


def test_retrieval_presets_use_identical_scope():
    client = Mock()
    scope = m.Filter(must=[m.FieldCondition(key="build_id", match=m.MatchValue(value="ready"))])
    search_points(client, "papers", [1., 0.], "star clusters", 5, "vanilla", scope)
    dense = client.query_points.call_args.kwargs
    assert "prefetch" not in dense
    assert dense["query_filter"] == scope
    search_points(client, "papers", [1., 0.], "star clusters", 20, "hybrid", scope)
    hybrid = client.query_points.call_args.kwargs
    assert hybrid["query_filter"] == scope
    assert hybrid["prefetch"][0].filter == scope
    assert scope in hybrid["prefetch"][1].filter.must


def test_empty_extraction_rejected():
    import pymupdf
    with pymupdf.open() as document:
        document.new_page()
        data = document.tobytes()
    with pytest.raises(ValueError, match="no extractable text"):
        extract_chunks(data, 100)
