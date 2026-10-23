"""Offline API, generation, Streamlit and frozen-run KG integration."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import Request, Response, HTTPException

from tests.unit.test_rag_presets import runtime
from src.api.kg.retrieval import KGUnavailable
from src.api.rag.modes.kg import KGContext
from src.api.api.models import RAGRequest


def test_kg_uses_shared_generation_and_preserves_citations(runtime, monkeypatch):
    from src.api.rag.modes import kg
    retrieval, _ = runtime
    contexts = KGContext([dict(id="point", text="Original text", title="Paper", page=2)],
                         dict(publication_id="pub", graph_used=True,hybrid_seconds=0.1,graph_seconds=0.2))
    monkeypatch.setattr(kg,"retrieve",Mock(return_value=contexts))
    monkeypatch.setattr(retrieval,"build_prompt",Mock(return_value=[]))
    monkeypatch.setattr(retrieval,"_resolve_required_papers",Mock(return_value=[]))
    generate = Mock(return_value=retrieval.RAGGenerationResponse(claims=[
        retrieval.RAGClaim(text="Supported fact",cited_context_ids=["point"],need_ids=[])]))
    monkeypatch.setattr(retrieval,"generate_answer",generate)
    result = retrieval.rag_pipeline("Question",Mock(),"session",mode="kg",scope=Mock(),catalogue=Mock(),kg_publication_id="pub")
    assert result["answer"] == "Supported fact [1]"
    assert result["sources"][0].id == "point"
    assert result["retrieval_diagnostics"]["publication_id"] == "pub"
    assert kg.retrieve.call_args.kwargs["publication_id"] == "pub"
    assert kg.retrieve.call_args.kwargs["required_papers"] == []
    generate.assert_called_once()


@pytest.mark.parametrize("failure",[False,True])
def test_kg_api_pins_memory_and_handles_unavailability(runtime,monkeypatch,failure):
    import src.api.api.papers_router as papers
    import src.api.kg.retrieval as graph
    _, router = runtime
    async def inline(function,*args,**kwargs):
        return function(*args,**kwargs)
    monkeypatch.setattr("starlette.concurrency.run_in_threadpool",inline)
    active = [dict(id="build",paper_id="paper",manifest=dict(point_ids=["point"]))]
    monkeypatch.setattr(papers,"active_corpus",lambda *args:(SimpleNamespace(PAPERS_COLLECTION="papers"),active,"snapshot"))
    pin = Mock(return_value=dict(publication_id="pub"))
    if failure:
        pin.side_effect = KGUnavailable("kg_publication_changed")
    monkeypatch.setattr(graph,"open_publication",pin)
    pipeline = Mock(return_value=dict(answer="Answer",sources=[],images=[],kg_retrieval=dict(publication_id="pub")))
    monkeypatch.setattr(router,"rag_pipeline_wrapper",pipeline)
    monkeypatch.setattr(router,"add_message",Mock())
    monkeypatch.setattr(router,"get_memory",Mock(return_value=SimpleNamespace(summary="",recent_messages=[])))
    req = Request({"type":"http","headers":[],"method":"POST","path":"/rag2"})
    req.state.request_id = "request"
    payload = RAGRequest(query="Question",mode="kg",corpus="arxiv",kg_publication_id="pub")
    if failure:
        with pytest.raises(HTTPException) as err:
            asyncio.run(router.rag(req,payload,Response()))
        assert err.value.status_code == 409
        pipeline.assert_not_called()
    else:
        result = asyncio.run(router.rag(req,payload,Response()))
        assert result.kg_retrieval["publication_id"] == "pub"
        assert pipeline.call_args.args[1].endswith(":pub")
        assert pipeline.call_args.kwargs["kg_publication_id"] == "pub"


def test_streamlit_kg_submission_details_and_pinning(monkeypatch):
    testing = pytest.importorskip("streamlit.testing.v1")
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root/"src/chatbot_ui"))
    response = Mock(status_code=200,headers={})
    response.json.return_value = dict(answer="Answer",sources=[],images=[],chat_history=[],
        corpus_snapshot="snapshot",kg_retrieval=dict(publication_id="pub",retrieval_status="graph_augmented",
            eligible_graph_paper_count=7,graph_paper_count=7,selected_graph_chunk_count=2,
            selection_policy="protected-hybrid-bounded-graph-v1",hybrid_protected_count=3,
            graph_expansion_count=2,graph_expansion_limit=2,graph_paper_scope="resolved_named_papers",
            graph_candidate_decisions=[dict(id="point",qualified=True,reason="qualified_graph_expansion")]))
    post = Mock(return_value=response)
    monkeypatch.setattr("requests.post",post)
    app = testing.AppTest.from_file(str(root/"src/chatbot_ui/main.py")).run(timeout=10)
    app.radio[0].set_value("kg").run(timeout=10)
    assert not app.exception
    app.text_input(key="user_question").set_value("Cluster Alpha?")
    next(w for w in app.button if w.label=="Ask").click().run(timeout=10)
    assert not app.exception
    assert post.call_args.kwargs["json"]["mode"] == "kg"
    assert app.session_state.kg_publication_id == "pub"
    assert any(w.label=="KG retrieval details" for w in app.expander)
    assert any("Protected Hybrid chunks: 3" in w.value for w in app.caption)
    assert any("restricted to the resolved named papers" in w.value for w in app.caption)
    next(w for w in app.button if w.label=="Start new conversation").click().run(timeout=10)
    assert "kg_publication_id" not in app.session_state


def test_benchmark_kg_pins_manifest_and_each_item(tmp_path,monkeypatch):
    from tests.unit.test_eval_runner import reviewed_dataset
    from evals import run_benchmark as runner
    import src.api.kg.retrieval as graph
    dataset = reviewed_dataset(tmp_path/"dataset")
    pin = Mock(return_value=dict(publication_id="pub",policy="hybrid-reviewed-graph-v1",manifest=dict(plan_id="plan")))
    monkeypatch.setattr(graph,"open_publication",pin)
    monkeypatch.setattr(runner,"QdrantClient",Mock())
    monkeypatch.setattr("src.api.papers.catalogue.Catalogue",Mock())
    evaluate = Mock(return_value=dict(question_id="q1",kind="single_paper",profile="single_fact",mode="kg",
        answer="Answer",metrics={},elapsed_seconds=0.1,error=None))
    monkeypatch.setattr(runner,"evaluate_item",evaluate)
    args=SimpleNamespace(dataset=dataset,output_root=tmp_path/"runs",run_id="test",modes=["kg"],limit=None,
        top_k=5,generation_model="offline",split="all",judge=False,judge_model="offline",
        judge_reasoning_effort="minimal",langfuse=False,concurrency=1,kg_publication_id="pub")
    output=runner.run(args)
    manifest=json.loads((output/"manifest.json").read_text())
    assert manifest["kg_configuration"]["publication_id"] == "pub"
    assert manifest["kg_configuration"]["selection_policy"] == "protected-hybrid-bounded-graph-v2"
    assert manifest["kg_configuration"]["max_graph_expansions"] == 2
    assert manifest["kg_configuration"]["fact_matching_policy"] == "named-assertion-literal-overlap-v1"
    assert manifest["kg_configuration"]["fact_matching_min_terms"] == 2
    assert evaluate.call_args.kwargs["kg_publication_id"] == "pub"
    assert manifest["modes"] == ["kg"]


def test_kg_summary_reports_hybrid_only_honestly():
    from evals import run_benchmark as runner
    result=runner.summarize([dict(mode="kg",kind="single_paper",elapsed_seconds=0.1,error=None,metrics={},
        retrieval_diagnostics=dict(policy="hybrid-reviewed-graph-v1",publication_id="pub",graph_used=False,
            selected_graph_chunk_count=0))],["kg"])
    assert result["kg"]["kg_retrieval"]["hybrid_only_runs"] == 1


@pytest.mark.parametrize("policy", ["hybrid-reviewed-graph-v2", "hybrid-reviewed-graph-v3", "hybrid-reviewed-graph-v4", "hybrid-reviewed-graph-v5"])
def test_kg_v2_summary_keeps_identity_and_diversity_diagnostics(policy):
    from evals import run_benchmark as runner
    result=runner.summarize([dict(mode="kg",kind="cross_paper",elapsed_seconds=0.1,error=None,metrics={},
        retrieval_diagnostics=dict(policy=policy,publication_id="pub",graph_used=True,
            selected_graph_chunk_count=2,cross_paper_entity_groups=[dict(catalogue_ids=["m22"])],
            paper_diversity_applied=True))],["kg"])
    summary=result["kg"]["kg_retrieval"]
    assert summary["graph_used_runs"] == 1
    assert summary["cross_paper_identity_runs"] == summary["paper_diversity_runs"] == 1


def test_v4_summary_distinguishes_graph_provenance_from_actual_expansion():
    from evals import run_benchmark as runner
    diagnostics = dict(policy="hybrid-reviewed-graph-v4",publication_id="pub",graph_used=False,
        selected_graph_chunk_count=1,graph_expansion_count=0,hybrid_protected_count=3,
        displaced_hybrid_chunks=[],graph_candidate_decisions=[dict(
            qualified=False,reason="no_specific_query_anchor")])
    row = dict(mode="kg",kind="single_paper",elapsed_seconds=0.1,error=None,metrics={},
               retrieval_diagnostics=diagnostics)
    summary = runner.summarize([row],["kg"])["kg"]["kg_retrieval"]
    assert summary["graph_used_runs"] == summary["graph_expansion_runs"] == 0
    assert summary["hybrid_only_runs"] == 1 and summary["mean_selected_graph_chunks"] == 1
    assert summary["graph_candidate_rejection_reasons"] == {"no_specific_query_anchor":1}
    report = runner.report_markdown(dict(run_id="test",dataset_hash="offline",modes=["kg"]),
                                    runner.summarize([row],["kg"]))
    assert "actual graph-expansion runs: 0" in report


def test_benchmark_summary_exposes_kg_codes_and_stages_without_fabricated_scores():
    from evals import run_benchmark as runner
    from evals.diagnostics import error_details
    error = error_details(KGUnavailable("kg_vector_graph_text_mismatch", stage="merge"))
    result = runner.summarize([dict(mode="kg", kind="single_paper", elapsed_seconds=0.1,
                                   error=error, metrics={})], ["kg"])["kg"]
    assert result["kg_failures"] == dict(runs=1, codes={"kg_vector_graph_text_mismatch": 1},
                                       stages={"merge": 1})
    assert result["metrics"] == {}
    assert result["errors"] == 1


def test_unregistered_kg_message_and_stage_are_never_public():
    from evals.diagnostics import error_details
    error = KGUnavailable("password=secret-private-URL", stage="token=secret")
    data = error_details(error)
    assert data["kg_failure"] == {"code": "kg_retrieval_unavailable_or_invalid"}
    assert "secret" not in json.dumps(data)
