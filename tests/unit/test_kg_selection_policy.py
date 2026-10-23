"""Offline bounded KG selection; synthetic provenance, no models or services."""
from types import SimpleNamespace

import pytest

from src.api.kg.selection_policy import select_expansion_context


def selection(*, limit=5, anchors=True, required=(), graph_build="a", overlap=False):
    seeds = [dict(collection="papers",id=f"h{i}",build_id="a",paper_id="paper-a",text="Hybrid evidence")
             for i in range(10)]
    graph = [dict(collection="papers",id=f"g{i}",build_id=graph_build,paper_id="paper-g",text="Graph evidence")
             for i in range(4)]
    if overlap:
        graph[0] = seeds[0]
    key = lambda r: (r["collection"],r["id"])
    rows = {key(r):r for r in [*seeds,*graph]}
    order = list(dict.fromkeys([*(key(r) for r in graph),*(key(r) for r in seeds)]))
    support = [dict(collection=r["collection"],id=r["id"],anchor_record_ids=["object"] if anchors else [])
               for r in graph]
    selected, diagnostics = select_expansion_context(order,rows,{key(r) for r in graph},
        hybrid_order=[key(r) for r in seeds],graph_support=support,limit=limit,query="A synthetic question",
        required_papers=required)
    return selected,diagnostics


def test_default_context_protects_three_hybrid_and_allows_two_qualified_additions():
    selected,d = selection()
    assert selected == [("papers",s) for s in ("h0","h1","h2","g0","g1")]
    assert d["hybrid_protected_count"] == 3
    assert d["graph_expansion_limit"] == d["graph_expansion_count"] == 2
    assert d["displaced_hybrid_chunks"] == [dict(collection="papers",id=s) for s in ("h3","h4")]
    assert [r["reason"] for r in d["graph_candidate_decisions"]] == [
        "qualified_graph_expansion","qualified_graph_expansion",
        "expansion_capacity_exhausted","expansion_capacity_exhausted"]


@pytest.mark.parametrize("limit",range(1,10))
def test_context_and_expansion_caps_hold_for_small_and_large_top_k(limit):
    selected,d = selection(limit=limit)
    assert len(selected) == len(set(selected)) == limit
    assert d["graph_expansion_count"] <= 2
    assert d["hybrid_protected_count"] >= limit-min(2,limit//2)
    assert all(r in selected for r in [("papers",f"h{i}") for i in range(d["hybrid_protected_count"])])


def test_weak_graph_matches_cannot_displace_any_hybrid_evidence():
    selected,d = selection(anchors=False)
    assert selected == [("papers",f"h{i}") for i in range(5)]
    assert d["graph_expansion_count"] == 0 and not d["displaced_hybrid_chunks"]
    assert all(r["reason"] == "no_specific_query_anchor" and not r["selected"]
               for r in d["graph_candidate_decisions"])


def test_graph_overlap_is_not_double_counted_as_a_new_context_passage():
    selected,d = selection(overlap=True)
    assert selected.count(("papers","h0")) == 1
    assert d["graph_candidate_decisions"][0]["reason"] == "already_in_hybrid_baseline"
    assert d["graph_candidate_decisions"][0]["selection_role"] == "protected_hybrid"
    assert d["graph_expansion_count"] == 2


@pytest.mark.parametrize("collection",["papers","wrong-collection"])
def test_explicit_paper_scope_is_an_exact_collection_and_build_pair(collection):
    selected,d = selection(required=[SimpleNamespace(collection=collection,build_id="a")],graph_build="b")
    assert selected == [("papers",f"h{i}") for i in range(5)]
    assert all(r["reason"] == "outside_requested_papers" for r in d["graph_candidate_decisions"])
    if collection != "papers":
        assert d["named_candidate_missing_build_ids"] == ["a"]


def test_selection_is_deterministic_and_does_not_mutate_original_passages():
    assert selection() == selection()


def test_no_promotion_preserves_named_baseline_order_not_just_membership():
    rows = {("papers",f"h{i}"):dict(collection="papers",id=f"h{i}",build_id="b" if i==4 else "a",
        paper_id="b" if i==4 else "a",text="Original Hybrid text") for i in range(5)}
    order = list(rows)
    selected,d = select_expansion_context(order,rows,{order[-1]},hybrid_order=order,
        graph_support=[],limit=5,query="Compare two named papers",required_papers=[
            SimpleNamespace(collection="papers",build_id=b) for b in ["a","b"]])
    assert selected == order
    assert not d["graph_expansion_count"] and not d["displaced_hybrid_chunks"]


def test_named_reservations_can_reduce_graph_allocation_below_two():
    rows = {("papers",f"h{i}"):dict(collection="papers",id=f"h{i}",build_id=f"b{i}",
        paper_id=f"p{i}",text="Hybrid text") for i in range(5)}
    key = ("papers","g")
    rows[key] = dict(collection="papers",id="g",build_id="b0",paper_id="p0",text="Graph text")
    hybrid_order = list(rows)[:-1]
    selected,d = select_expansion_context([key,*hybrid_order],rows,{key},hybrid_order=hybrid_order,
        graph_support=[dict(collection="papers",id="g",anchor_record_ids=["object"])],
        limit=5,query="Compare named papers",required_papers=[
            SimpleNamespace(collection="papers",build_id=f"b{i}") for i in range(4)])
    assert set(hybrid_order[:4]).issubset(selected)
    assert d["hybrid_protected_count"] == 4
    assert d["graph_expansion_limit"] == d["graph_expansion_count"] == 1
    assert d["named_selected_missing_build_ids"] == []


def test_direct_requested_fact_can_qualify_without_entity_path_and_outranks_entity_only():
    seeds = {("papers",f"h{i}"):dict(collection="papers",build_id="b",paper_id="p",text="Hybrid")
             for i in range(5)}
    graph = {("papers",k):dict(collection="papers",build_id="b",paper_id="p",text="Original graph text")
             for k in ["entity-a","entity-b","fact"]}
    order = [*graph,*seeds]
    support = [dict(collection="papers",id=k,anchor_record_ids=["object"]) for k in ["entity-a","entity-b"]]
    support.append(dict(collection="papers",id="fact",anchor_record_ids=[],fact_record_id="assertion",
                        fact_record_kind="measurement",matched_fact_terms=["tracer","flux"]))
    selected,d = select_expansion_context(order,seeds|graph,set(graph),hybrid_order=list(seeds),
        graph_support=support,limit=5,query="Report tracer flux",required_papers=[
            SimpleNamespace(collection="papers",build_id="b")])
    assert selected[:3] == list(seeds)[:3]
    assert selected[3:] == [("papers","fact"),("papers","entity-a")]
    decision = next(r for r in d["graph_candidate_decisions"] if r["id"]=="fact")
    assert decision["qualified"] and decision["qualification_basis"] == "named_paper_fact_overlap"
    assert d["graph_expansion_count"] == 2
