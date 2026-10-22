"""Rank-only named-paper reservations; no service, model or gold evidence access."""
from types import SimpleNamespace
from unittest.mock import Mock

from src.api.rag.modes.hybrid import retrieve
from src.api.rag.modes.named_selection import select_named_context
from src.api.kg.selection_policy import select_context


def paper(build, collection="papers"):
    return SimpleNamespace(build_id=build, collection=collection)


def rows():
    return [dict(id=f"a{i}", paper_id="paper-a", build_id="a", collection="papers", text="A")
            for i in range(6)] + [dict(id="b1", paper_id="paper-b", build_id="b",
                                      collection="papers", text="B")]


def test_hybrid_fetches_one_candidate_pool_and_reserves_each_resolved_build():
    search = Mock(return_value=rows())
    context = retrieve("Compare named titles", Mock(), top_k=3, collection="papers",
                       scope="frozen", retrieve_context=search, required_papers=[paper("a"), paper("b")])
    assert [r["id"] for r in context] == ["a0", "a1", "b1"]
    search.assert_called_once()
    assert search.call_args.kwargs["top_k"] == 20
    assert search.call_args.kwargs["scope"] == "frozen"
    assert context.diagnostics["named_paper_diversity_guard_applied"]
    assert context.diagnostics["named_selected_missing_build_ids"] == []


def test_ordinary_hybrid_query_is_unchanged():
    original = rows()[:3]
    search = Mock(return_value=original)
    assert retrieve("ordinary", Mock(), top_k=3, collection="papers", scope="scope",
                    retrieve_context=search) is original
    search.assert_called_once()
    assert search.call_args.kwargs["top_k"] == 3


def test_missing_named_candidate_is_reported_not_invented():
    result = select_named_context(rows(), [paper("a"), paper("missing")], 3)
    assert len(result) == 3
    assert result.diagnostics["named_candidate_missing_build_ids"] == ["missing"]
    assert result.diagnostics["named_selected_missing_build_ids"] == ["missing"]


def test_same_paper_id_in_another_build_or_collection_is_not_reserved():
    candidate = rows()[-1] | dict(build_id="old-b")
    result = select_named_context(rows()[:6] + [candidate], [paper("b")], 3)
    assert result.diagnostics["reserved_candidate_ids"] == []
    candidate["build_id"] = "b"
    candidate["collection"] = "other-collection"
    result = select_named_context(rows()[:6] + [candidate], [paper("b")], 3)
    assert result.diagnostics["reserved_candidate_ids"] == []


def test_more_named_papers_than_context_slots_cannot_exceed_top_k():
    result = select_named_context(rows(), [paper("a"), paper("b")], 1)
    assert len(result) == 1
    assert result.diagnostics["named_selected_missing_build_ids"] == ["b"]


def test_kg_named_reservations_take_priority_over_an_unrelated_graph_slot():
    source = rows() + [dict(id="g", paper_id="other", build_id="g", collection="papers", text="Graph")]
    order = [(r["collection"], r["id"]) for r in source]
    mapping = dict(zip(order, source))
    selected, diagnostics = select_context(order, mapping, {order[-1]}, limit=2, query="Compare papers",
                                         required_papers=[paper("a"), paper("b")])
    assert selected == [order[0], order[-2]]
    assert diagnostics["named_selected_missing_build_ids"] == []


def test_kg_reserves_graph_and_named_papers_when_slots_allow():
    source = rows() + [dict(id="g", paper_id="other", build_id="g", collection="papers", text="Graph")]
    order = [(r["collection"], r["id"]) for r in source]
    selected, _ = select_context(order, dict(zip(order, source)), {order[-1]}, limit=3,
                                 query="Compare papers", required_papers=[paper("a"), paper("b")])
    assert selected == [order[0], order[-2], order[-1]]
