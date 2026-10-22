"""KG RAG: Hybrid seeds + scoped reviewed graph expansion + shared generation."""
from time import monotonic
from src.api.kg.retrieval import KGReader, KGUnavailable, POLICY
from src.api.kg.settings import KGSettings
from src.api.rag.contracts import RetrievalScope, FederatedRetrievalScope
from src.api.observability.tracing import observe, observation, update_span
from src.api.kg.selection_policy import select_context, survey_requested


class KGContext(list):
    def __init__(self, rows, diagnostics):
        super().__init__(rows)
        self.diagnostics = diagnostics


@observe(name="kg_retrieval", as_type="retriever", capture_input=False, capture_output=False)
def retrieve(query, client, *, top_k, collection, scope, catalogue, retrieve_context,
             publication_id=None, reader=None, settings=None, required_papers=()):
    if catalogue is None or not isinstance(scope, (RetrievalScope, FederatedRetrievalScope)):
        raise KGUnavailable("kg_explicit_catalogue_scope_required")
    owned = reader is None
    failed = False
    stage = "configuration"
    try:
        settings = settings or KGSettings()
        stage = "connect"
        reader = reader or KGReader.connect(settings)
        stage = "pin"
        pinned = reader.publication(publication_id)
        started = monotonic()
        stage = "hybrid_search"
        candidate_limit = (max(top_k, settings.KG_QUERY_HYBRID_CANDIDATES)
                           if required_papers or survey_requested(query) else top_k)
        seeds = retrieve_context(query, client, top_k=candidate_limit, mode="hybrid", collection=collection, scope=scope)
        hybrid_seconds = monotonic()-started
        started = monotonic()
        stage = "graph_search"
        with observation(name="kg_graph_retrieval", as_type="retriever", input={"query":query}) as span:
            graph = reader.search(query, scope=scope, catalogue=catalogue, seeds=seeds,
                                  limit=settings.KG_QUERY_MAX_CHUNKS, expected=pinned["publication_id"])
            if span is not None:
                span.update(metadata=graph.diagnostics, output={"chunk_ids":[r.id for r in graph.chunks]})
        graph_seconds = monotonic()-started
        stage = "merge"
        rows = { (r["collection"], r["id"]):dict(r) for r in seeds }
        graph_rows = [r.model_dump() for r in graph.chunks]
        scores = {}
        for result in (seeds, graph_rows):
            for rank, row in enumerate(result, 1):
                key = (row["collection"], row["id"])
                # SourceChunk validation strips boundary whitespace while legacy
                # Qdrant payloads may retain a final newline. Never normalize inner
                # whitespace, numeric signs, wording or the returned original text.
                if key in rows and rows[key]["text"].strip() != row["text"].strip():
                    raise KGUnavailable("kg_vector_graph_text_mismatch")
                rows.setdefault(key, row)
                scores[key] = scores.get(key, 0) + 1/(60+rank)
        order = sorted(scores, key=lambda key:(-scores[key], key))
        # Reserve a graph-supported slot when named-paper coverage leaves capacity.
        # This is observable, not a claim that every graph candidate is relevant.
        graph_keys = {(r["collection"], r["id"]) for r in graph_rows}
        stage = "selection"
        selected, coverage = select_context(order, rows, graph_keys, limit=top_k, query=query,
            resolved_ids=graph.diagnostics.get("resolved_catalogue_ids", []),
            required_papers=required_papers)
        if len({key[1] for key in selected}) != len(selected):
            raise KGUnavailable("kg_ambiguous_citation_identity")
        stage = "recheck"
        reader.publication(pinned["publication_id"])
        graph_used = bool(graph_keys.intersection(selected))
        diagnostics = graph.diagnostics | coverage | dict(policy=POLICY, hybrid_seed_count=len(seeds),
            hybrid_candidate_limit=candidate_limit,
            selected_graph_chunk_count=len(graph_keys.intersection(selected)),
            selected_chunk_count=len(selected), graph_used=graph_used,
            hybrid_seconds=round(hybrid_seconds,3), graph_seconds=round(graph_seconds,3),
            retrieval_status=("graph_augmented" if graph_used else
                              "hybrid_only_graph_not_selected" if graph_rows else "hybrid_only_no_graph_match"))
        diagnostics.update(candidate_count=len(rows),
            candidate_paper_ids=sorted({r["paper_id"] for r in rows.values()}),
            candidate_paper_count=len({r["paper_id"] for r in rows.values()}),
            selected_paper_ids=sorted({rows[key]["paper_id"] for key in selected}),
            selected_paper_count=len({rows[key]["paper_id"] for key in selected}))
        update_span(metadata=diagnostics, output={"chunk_ids":[key[1] for key in selected]})
        return KGContext([rows[key] | dict(score=scores[key]) for key in selected], diagnostics)
    except KGUnavailable as error:
        failed = True
        if error.stage is None:
            error.stage = stage
        raise
    except Exception as error:
        failed = True
        raise KGUnavailable("kg_retrieval_unavailable_or_invalid", stage=stage) from error
    finally:
        if owned and reader is not None:
            try:
                reader.close()
            except Exception as error:
                if not failed:
                    raise KGUnavailable("kg_close_failed", stage="close") from error
