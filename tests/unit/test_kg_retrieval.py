"""KG runtime: deterministic scoped graph evidence, no services/.env/model calls."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.api.kg.retrieval import (
    KGReader, KGUnavailable, canonical, identity, eligible_builds, mentioned,
    validate_records, validate_sources,
)
from src.api.kg.settings import KGSettings
from src.api.rag.contracts import RetrievalScope, ScopedBuild, FederatedRetrievalScope
from src.api.rag.modes.kg import retrieve


class Result(list):
    def single(self):
        assert len(self) <= 1
        return self[0] if self else None


@pytest.fixture
def graph():
    paper, build, point = map(str, (uuid4(), uuid4(), uuid4()))
    pub = "publication:synthetic"
    text = "Cluster Alpha (A1) lies in Region Beta. Its distance is 7 kpc."
    source = dict(paper_id=paper, build_id=build, collection="papers", point_id=point,
                  source="arxiv", page_number=2, section_header="Results")
    entity = dict(id="e1", kind="astronomical_object", name="Cluster Alpha", aliases=["A1"],
                  evidence=[source | dict(quote="Cluster Alpha (A1)")])
    obs = dict(id="o1", subject_id="e1", kind="measurement", statement="Distance is 7 kpc.",
               quantity="distance", value_text="7", unit_text="kpc", conditions=[],
               evidence=[source | dict(quote="Its distance is 7 kpc.")])
    entities = [entity, dict(id="e2", kind="spatial_region", name="Region Beta", aliases=[],
                            evidence=[source | dict(quote="Region Beta")])]
    rel = dict(id="r1", subject_id="e1", object_id="e2", predicate="located_in", epistemic_status="reported",
               evidence=[source | dict(quote="Cluster Alpha (A1) lies in Region Beta.")])
    records, sources, edges = [], [], []
    chunk = source | dict(id=identity("chunk", "papers", point), text=text,
        text_sha256=sha256(text.encode()).hexdigest(), chunk_index=4)
    for kind, label, record in [("entity","KGEntity",r) for r in entities] + [("observation","KGObservation",obs),("relationship","KGRelationship",rel)]:
        key = identity("record", pub, record["id"])
        records.append(dict(record=dict(id=key, publication_id=pub, record_id=record["id"],
            record_type=kind, build_id=build, paper_id=paper, collection="papers",
            record_json=canonical(record), review_json=canonical(dict(decision="approved", reviewer="offline reviewer"))),
            labels=["KGRecord", label]))
        for evidence in record["evidence"]:
            sources.append(dict(record_id=key, support=dict(publication_id=pub, quote=evidence["quote"],
                                                            evidence_json=canonical(evidence)), chunk=chunk))
    b = dict(build_id=build, paper_id=paper, collection="papers", source="arxiv", version=1,
             title="Cluster Alpha Study", manifest_sha256="verified")
    row = dict(id=build, paper_id=paper, collection="papers", source="arxiv", source_id="2601.12345",
               version=1, status="ready", deleted=False, active_build=build,
               manifest=dict(artifact=dict(sha256="verified")), metadata=dict(authors=["A. Author"]))
    settings = KGSettings(_env_file=None)
    manifest = dict(publication_id=pub, writer_version="kg-publication-v1", graph_name=settings.KG_GRAPH_NAME,
        extraction_revision="reviewed-offline", plan_id="plan", counts=dict(papers=1, records=4))
    g = SimpleNamespace(build=build, paper=paper, point=point, publication=pub, text=text,
        records=records, sources=sources, builds=[b], row=row, settings=settings, manifest=manifest,
        catalogue=SimpleNamespace(scoped_ready_builds=Mock(return_value=[row])), calls=[])
    g.scope = RetrievalScope("papers", (build,), builds=(ScopedBuild(build, paper, (point,)),))

    class Tx:
        def run(self, query, **params):
            g.calls.append((query, params))
            assert not any(word in query for word in ("CREATE ", "MERGE ", "SET ", "DELETE "))
            if "KGCorpus" in query:
                return Result([dict(id=g.publication, manifest=canonical(g.manifest))])
            if "RETURN properties(b)" in query:
                return Result([dict(build=b) for b in g.builds])
            if "RETURN properties(r)" in query:
                return Result([r for r in g.records if r["record"]["build_id"] in params["builds"]])
            if "RETURN r.id AS record_id" in query:
                return Result([r for r in g.sources if r["record_id"] in params["records"]])
            if "MATCH path=" in query:
                # Exact structural adjacency from the application-supplied approved links.
                distance = {key:0 for key in params["seeds"]}
                for _ in range(2):
                    for edge in params["links"]:
                        for a,b in [(edge["start"], edge["end"]), (edge["end"], edge["start"])]:
                            if a in distance and distance[a] < 2:
                                distance[b] = min(distance.get(b, 99), distance[a]+1)
                return Result([dict(id=k,distance=v) for k,v in distance.items()])
            raise AssertionError(query)

    class Reader(KGReader):
        @contextmanager
        def transaction(self):
            yield Tx()
    g.reader = Reader(None, settings)
    return g


def test_exact_alias_matching_not_substrings_or_inferred_aliases():
    assert mentioned("ω Centauri", "What about Ω CENTAURI?")
    assert mentioned("A1", "Distance of (A1)?")
    assert not mentioned("M22", "M220 and M222")
    assert not mentioned("M22", "NGC 6656")
    assert not mentioned("a", "a star")


@pytest.mark.parametrize("name,query", [
    ("M 22", "What about M22?"), ("M22", "M\u202f22"),
    ("NGC 6656", "NGC6656"), ("IC10", "IC 10"),
    ("NGC 123A", "NGC123a"),
])
def test_catalogue_spacing_and_case_are_formatting_not_new_aliases(name, query):
    assert mentioned(name, query)


@pytest.mark.parametrize("name,query", [
    ("M22", "M220 M222 M22A"), ("M22", "M22_stars_sample"),
    ("NGC6656", "NGC6656A"), ("A 1", "A1"), ("M22", "NGC 6656"),
])
def test_catalogue_normalization_does_not_infer_components_or_unknown_catalogues(name, query):
    assert not mentioned(name, query)


def add_object_paper(g, name, aliases, text, value="4"):
    """Distinct source/record identities; even contradictory values stay separate."""
    paper, build, point = map(str, (uuid4(), uuid4(), uuid4()))
    source = dict(paper_id=paper,build_id=build,collection="papers",point_id=point,
                  source="arxiv",page_number=1,section_header="Results")
    entity_id = build+":entity"
    entity = dict(id=entity_id,kind="astronomical_object",name=name,aliases=aliases,
                  evidence=[source|dict(quote=text)])
    obs = dict(id=build+":observation",subject_id=entity_id,kind="measurement",
        statement=f"Distance is {value} kpc.",quantity="distance",value_text=value,unit_text="kpc",
        conditions=[],evidence=[source|dict(quote=text)])
    chunk = source|dict(id=identity("chunk","papers",point),text=text,
                       text_sha256=sha256(text.encode()).hexdigest(),chunk_index=0)
    for kind,label,record in (("entity","KGEntity",entity),("observation","KGObservation",obs)):
        key = identity("record",g.publication,record["id"])
        g.records.append(dict(record=dict(id=key,publication_id=g.publication,record_id=record["id"],
            record_type=kind,build_id=build,paper_id=paper,collection="papers",record_json=canonical(record),
            review_json=canonical(dict(decision="approved",reviewer="offline reviewer"))),labels=["KGRecord",label]))
        g.sources.append(dict(record_id=key,support=dict(publication_id=g.publication,quote=text,
                                                       evidence_json=canonical(source|dict(quote=text))),chunk=chunk))
    g.builds.append(dict(build_id=build,paper_id=paper,collection="papers",source="arxiv",version=1,
                        title=name+" Study",manifest_sha256="verified"))
    row = dict(g.row,id=build,paper_id=paper,active_build=build)
    g.rows = [*getattr(g,"rows",[g.row]),row]
    g.catalogue.scoped_ready_builds.return_value = g.rows
    g.scope = RetrievalScope("papers",tuple(b["build_id"] for b in g.builds),
        builds=(*g.scope.builds,ScopedBuild(build,paper,(point,))))
    g.manifest["counts"] = dict(papers=len(g.builds),records=len(g.records))
    return paper, point, row


def test_source_backed_catalogue_aliases_resolve_across_papers_without_merging_measurements(graph):
    a,point_a,_ = add_object_paper(graph,"M22",["NGC 6656"],"M 22 (NGC 6656): distance is 4 kpc.")
    b,point_b,_ = add_object_paper(graph,"NGC6656",[],"NGC 6656: distance is 9 kpc.",value="9")
    result = graph.reader.search("What do papers report about M22?",scope=graph.scope,
        catalogue=graph.catalogue,seeds=[],limit=2)
    assert {c.id for c in result.chunks} == {point_a,point_b}
    assert {c.paper_id for c in result.chunks} == {a,b}
    assert result.diagnostics["resolved_catalogue_ids"] == ["m22","ngc6656"]
    assert len(result.diagnostics["cross_paper_entity_groups"]) == 1
    assert result.diagnostics["identity_expanded_seed_count"] == 1
    assert any("4 kpc" in c.text for c in result.chunks)
    assert any("9 kpc" in c.text for c in result.chunks)


def test_conflicting_catalogue_bridges_do_not_expand_to_third_paper(graph):
    add_object_paper(graph,"M22",["NGC6656"],"M22 (NGC6656): distance is 4 kpc.")
    add_object_paper(graph,"NGC6656",[],"NGC6656: distance is 4 kpc.")
    _,conflicting,_ = add_object_paper(graph,"NGC9999",["M22"],"M22 (NGC9999): distance is 4 kpc.")
    result = graph.reader.search("NGC6656",scope=graph.scope,catalogue=graph.catalogue,seeds=[],limit=20)
    assert conflicting not in {c.id for c in result.chunks}
    assert result.diagnostics["entity_resolution_conflicts"]
    assert not result.diagnostics["cross_paper_entity_groups"]


def test_unquoted_alias_cannot_supply_cross_paper_identity_bridge(graph):
    add_object_paper(graph,"M22",["NGC6656"],"M22: distance is 4 kpc.")
    _,other,_ = add_object_paper(graph,"NGC6656",[],"NGC6656: distance is 4 kpc.")
    result = graph.reader.search("M22",scope=graph.scope,catalogue=graph.catalogue,seeds=[],limit=20)
    assert other not in {c.id for c in result.chunks}


def test_ineligible_paper_cannot_join_identity_group(graph):
    add_object_paper(graph,"M22",["NGC6656"],"M22 (NGC6656): distance is 4 kpc.")
    _,other,row = add_object_paper(graph,"NGC6656",[],"NGC6656: distance is 4 kpc.")
    row["deleted"] = True
    result = graph.reader.search("M22",scope=graph.scope,catalogue=graph.catalogue,seeds=[],limit=20)
    assert other not in {c.id for c in result.chunks}
    assert not result.diagnostics["cross_paper_entity_groups"]


def test_generic_names_are_not_used_for_cross_paper_resolution(graph):
    _,other,_ = add_object_paper(graph,"Cluster Alpha",[],"Cluster Alpha: distance is 4 kpc.")
    result = graph.reader.search("distance",scope=graph.scope,catalogue=graph.catalogue,
        seeds=[dict(collection="papers",id=graph.point)],limit=20)
    assert other not in {c.id for c in result.chunks}


def test_survey_selection_considers_more_candidates_but_keeps_top_k_and_graph_slot(graph):
    add_object_paper(graph,"M22",[],"M22: distance is 4 kpc.")
    seeds = [dict(id=f"a{i}",collection="papers",paper_id="a",text="M 22 abundance study.") for i in range(5)]
    seeds += [dict(id="b",collection="papers",paper_id="b",text="M22 variables.")]
    seeds += [dict(id="unrelated",collection="papers",paper_id="c",text="A galaxy survey.")]
    search = Mock(return_value=seeds)
    result = retrieve("What do papers report about M22?",Mock(),top_k=3,collection="papers",scope=graph.scope,
        catalogue=graph.catalogue,retrieve_context=search,reader=graph.reader,settings=graph.settings)
    assert search.call_args.kwargs["top_k"] == graph.settings.KG_QUERY_HYBRID_CANDIDATES
    assert len(result) == 3 and len({r["paper_id"] for r in result}) == 3
    assert result.diagnostics["selected_graph_chunk_count"] == 1
    assert result.diagnostics["paper_diversity_applied"]
    assert "unrelated" not in {r["id"] for r in result}


def test_single_fact_does_not_enable_larger_survey_pool(graph):
    search = Mock(return_value=[])
    retrieve("Distance of A1?",Mock(),top_k=2,collection="papers",scope=graph.scope,
        catalogue=graph.catalogue,retrieve_context=search,reader=graph.reader,settings=graph.settings)
    assert search.call_args.kwargs["top_k"] == 2


def test_graph_reservation_prefers_literal_subject_over_unrelated_graph_hit():
    from src.api.kg.selection_policy import select_context
    rows = {"unrelated":dict(paper_id="other",text="47 Tuc stars."),
            "target":dict(paper_id="m22",text="M 22 abundances.")}
    chosen,_ = select_context(list(rows),rows,set(rows),limit=1,
                             query="What do papers report about M22?")
    assert chosen == ["target"]


def test_graph_traversal_returns_original_scoped_chunk_and_attribution(graph):
    result = graph.reader.search("Cluster Alpha distance", scope=graph.scope,
        catalogue=graph.catalogue, seeds=[], limit=5)
    assert len(result.chunks) == 1
    chunk = result.chunks[0]
    assert chunk.text == graph.text and chunk.id == graph.point and chunk.chunk_index == 4
    assert chunk.source_url == "https://arxiv.org/abs/2601.12345v1" and chunk.authors == ["A. Author"]
    assert result.diagnostics["matched_entity_ids"]
    assert len(result.diagnostics["traversed_record_ids"]) == 4
    assert result.diagnostics["database_writes"] == 0
    path, args = next((q,p) for q,p in graph.calls if "MATCH path=" in q)
    assert "*0..2" in path and "all(n IN nodes(path)" in path and "all(e IN relationships(path)" in path
    assert "startNode(e).id" in path and args["links"]


def test_hybrid_point_seeds_without_entity_mention(graph):
    result = graph.reader.search("distance", scope=graph.scope, catalogue=graph.catalogue,
        seeds=[dict(collection="papers",id=graph.point)], limit=5)
    assert not result.diagnostics["matched_entity_ids"] and result.chunks


@pytest.mark.parametrize("change", [dict(deleted=True),dict(status="failed"),dict(active_build="new"),
    dict(paper_id="wrong"),dict(collection="other"),dict(source="uploads"),dict(version=2),
    dict(manifest=None),dict(manifest=dict(artifact=dict(sha256="changed")))])
def test_ineligible_sources_cannot_reach_traversal(graph, change):
    graph.row.update(change)
    result = graph.reader.search("Cluster Alpha", scope=graph.scope, catalogue=graph.catalogue, seeds=[], limit=5)
    assert not result.chunks and result.diagnostics["eligible_graph_paper_count"] == 0


def test_frozen_ready_retained_build_allowed_but_never_deleted(graph):
    graph.row["active_build"] = "replacement"
    frozen = RetrievalScope("papers",(graph.build,),kind="frozen")
    assert eligible_builds(graph.builds, frozen, graph.catalogue)
    assert graph.catalogue.scoped_ready_builds.call_args.kwargs["active_only"] is False
    graph.row["deleted"] = True
    assert not eligible_builds(graph.builds, frozen, graph.catalogue)


def test_federated_scope_and_wrong_paper_filter(graph):
    scope = FederatedRetrievalScope((graph.scope, RetrievalScope("uploads",("other",))))
    assert graph.reader.search("A1", scope=scope, catalogue=graph.catalogue,seeds=[],limit=5).chunks
    wrong = RetrievalScope("papers",(graph.build,),paper_ids=("other",))
    assert not eligible_builds(graph.builds, wrong, graph.catalogue)


@pytest.mark.parametrize("field", ["text", "quote", "publication", "evidence", "review", "dependency"])
def test_corruption_fails_closed(graph, field):
    if field == "text":
        graph.sources[0]["chunk"]["text"] = "tampered"
    elif field == "quote":
        graph.sources[0]["support"]["quote"] = "invented"
    elif field == "publication":
        graph.records[0]["record"]["publication_id"] = "other"
    elif field == "evidence":
        graph.sources.pop()
    elif field == "review":
        graph.records[0]["record"]["review_json"] = canonical(dict(decision="needs_review", reviewer="reviewer"))
    else:
        graph.records.pop(0)
    with pytest.raises(KGUnavailable):
        graph.reader.search("A1", scope=graph.scope, catalogue=graph.catalogue,seeds=[],limit=5)


def test_pinned_publication_and_size_bounds_fail_before_search(graph):
    with pytest.raises(KGUnavailable,match="publication_changed"):
        graph.reader.publication("old")
    graph.settings.KG_QUERY_MAX_RECORDS = 1
    with pytest.raises(KGUnavailable,match="record_limit"):
        graph.reader.publication()


def test_no_graph_match_is_observable_hybrid_only_not_a_hidden_fallback(graph):
    seed = dict(id="unreviewed-point", collection="papers", text="Full corpus evidence", paper_id=graph.paper)
    search = Mock(return_value=[seed])
    result = retrieve("unrelated",Mock(),top_k=5,collection="papers",scope=graph.scope,
        catalogue=graph.catalogue,retrieve_context=search,reader=graph.reader,settings=graph.settings)
    assert result[0]["id"] == seed["id"]
    assert result.diagnostics["retrieval_status"] == "hybrid_only_no_graph_match"
    assert not result.diagnostics["graph_used"]
    assert search.call_args.kwargs["mode"] == "hybrid"


def test_graph_slot_and_final_context_cap_without_cohere(graph):
    seed = dict(id="unreviewed", collection="papers", text="Hybrid evidence", paper_id=graph.paper)
    result = retrieve("Cluster Alpha",Mock(),top_k=1,collection="papers",scope=graph.scope,
        catalogue=graph.catalogue,retrieve_context=Mock(return_value=[seed]),reader=graph.reader,settings=graph.settings)
    assert len(result)==1 and result[0]["id"] == graph.point
    assert result.diagnostics["selected_graph_chunk_count"] == 1


def test_vector_graph_text_conflict_is_not_silently_overwritten(graph):
    seed = dict(id=graph.point,collection="papers",text="changed",paper_id=graph.paper)
    with pytest.raises(KGUnavailable,match="text_mismatch"):
        retrieve("A1",Mock(),top_k=5,collection="papers",scope=graph.scope,
            catalogue=graph.catalogue,retrieve_context=Mock(return_value=[seed]),reader=graph.reader,settings=graph.settings)


@pytest.mark.parametrize("boundary", ["\n", "  ", "\r\n"])
def test_vector_graph_boundary_whitespace_preserves_original_text(graph, boundary):
    original = boundary + graph.text + boundary
    seed = dict(id=graph.point, collection="papers", text=original, paper_id=graph.paper,
                build_id=graph.build)
    result = retrieve("A1", Mock(), top_k=5, collection="papers", scope=graph.scope,
        catalogue=graph.catalogue, retrieve_context=Mock(return_value=[seed]),
        reader=graph.reader, settings=graph.settings)
    assert next(r["text"] for r in result if r["id"] == graph.point) == original
    assert result.diagnostics["graph_used"]


@pytest.mark.parametrize("changed", ["7  kpc", "9 kpc", "-7 kpc", "7 Kpc"])
def test_vector_graph_inner_content_changes_remain_fail_closed(graph, changed):
    seed = dict(id=graph.point, collection="papers", text=graph.text.replace("7 kpc", changed),
                paper_id=graph.paper, build_id=graph.build)
    with pytest.raises(KGUnavailable) as caught:
        retrieve("A1", Mock(), top_k=5, collection="papers", scope=graph.scope,
            catalogue=graph.catalogue, retrieve_context=Mock(return_value=[seed]),
            reader=graph.reader, settings=graph.settings)
    assert caught.value.code == "kg_vector_graph_text_mismatch"
    assert caught.value.stage == "merge"


@pytest.mark.parametrize("stage", ["pin", "hybrid_search", "graph_search"])
def test_unexpected_kg_errors_record_stage_without_raw_messages(graph, stage):
    reader = Mock(wraps=graph.reader)
    search = Mock(return_value=[])
    secret = "private-host-and-password-must-not-be-serialized"
    if stage == "pin":
        reader.publication.side_effect = RuntimeError(secret)
    elif stage == "hybrid_search":
        search.side_effect = RuntimeError(secret)
    else:
        reader.search.side_effect = RuntimeError(secret)
    with pytest.raises(KGUnavailable) as caught:
        retrieve("A1", Mock(), top_k=5, collection="papers", scope=graph.scope,
            catalogue=graph.catalogue, retrieve_context=search, reader=reader, settings=graph.settings)
    from evals.diagnostics import error_details
    details = error_details(caught.value)
    assert details["category"] == "kg_retrieval"
    assert details["kg_failure"] == dict(code="kg_retrieval_unavailable_or_invalid", stage=stage)
    assert secret not in json.dumps(details)
    reader.close.assert_not_called()  # Caller-owned reader.


def test_owned_reader_close_cannot_mask_the_primary_failure(graph, monkeypatch):
    reader = Mock()
    reader.publication.side_effect = KGUnavailable("kg_no_active_publication")
    reader.close.side_effect = RuntimeError("secondary private error")
    monkeypatch.setattr(KGReader, "connect", Mock(return_value=reader))
    with pytest.raises(KGUnavailable) as caught:
        retrieve("A1", Mock(), top_k=5, collection="papers", scope=graph.scope,
            catalogue=graph.catalogue, retrieve_context=Mock(), settings=graph.settings)
    assert caught.value.code == "kg_no_active_publication"
    assert caught.value.stage == "pin"
    reader.close.assert_called_once()


def test_connect_failure_is_safe_and_stage_labelled(graph, monkeypatch):
    monkeypatch.setattr(KGReader, "connect", Mock(side_effect=RuntimeError("private endpoint")))
    with pytest.raises(KGUnavailable) as caught:
        retrieve("A1", Mock(), top_k=5, collection="papers", scope=graph.scope,
            catalogue=graph.catalogue, retrieve_context=Mock(), settings=graph.settings)
    assert caught.value.stage == "connect"


def test_mid_query_sql_change_fails_closed(graph):
    graph.catalogue.scoped_ready_builds.side_effect = [[deepcopy(graph.row)], []]
    with pytest.raises(KGUnavailable,match="source_scope_changed"):
        graph.reader.search("A1",scope=graph.scope,catalogue=graph.catalogue,seeds=[],limit=5)


def test_mode_fails_before_hybrid_on_missing_publication(graph):
    reader = Mock()
    reader.publication.side_effect = KGUnavailable("kg_no_active_publication")
    search = Mock()
    with pytest.raises(KGUnavailable):
        retrieve("query",Mock(),top_k=5,collection="papers",scope=graph.scope,
            catalogue=graph.catalogue,retrieve_context=search,reader=reader,settings=graph.settings)
    search.assert_not_called()


def test_source_link_limit_is_explicit_not_a_truncated_projection(graph):
    graph.settings.KG_QUERY_MAX_SOURCE_LINKS=1
    with pytest.raises(KGUnavailable,match="source_link_limit"):
        graph.reader.search("A1",scope=graph.scope,catalogue=graph.catalogue,seeds=[],limit=5)
