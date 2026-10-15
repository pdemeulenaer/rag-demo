"""KG RAG: Hybrid seeds + scoped reviewed graph expansion + shared generation."""
from time import monotonic
from src.api.kg.retrieval import KGReader, KGUnavailable, POLICY
from src.api.kg.settings import KGSettings
from src.api.rag.contracts import RetrievalScope, FederatedRetrievalScope
from src.api.observability.tracing import observe, observation, update_span


class KGContext(list):
    def __init__(self, rows, diagnostics):
        super().__init__(rows)
        self.diagnostics = diagnostics


@observe(name="kg_retrieval", as_type="retriever", capture_input=False, capture_output=False)
def retrieve(query, client, *, top_k, collection, scope, catalogue, retrieve_context,
             publication_id=None, reader=None, settings=None):
    if catalogue is None or not isinstance(scope, (RetrievalScope, FederatedRetrievalScope)):
        raise KGUnavailable("kg_explicit_catalogue_scope_required")
    settings = settings or KGSettings()
    owned = reader is None
    reader = reader or KGReader.connect(settings)
    try:
        pinned = reader.publication(publication_id)
        started = monotonic()
        seeds = retrieve_context(query, client, top_k=top_k, mode="hybrid", collection=collection, scope=scope)
        hybrid_seconds = monotonic()-started
        started = monotonic()
        with observation(name="kg_graph_retrieval", as_type="retriever", input={"query":query}) as span:
            graph = reader.search(query, scope=scope, catalogue=catalogue, seeds=seeds,
                                  limit=settings.KG_QUERY_MAX_CHUNKS, expected=pinned["publication_id"])
            if span is not None:
                span.update(metadata=graph.diagnostics, output={"chunk_ids":[r.id for r in graph.chunks]})
        graph_seconds = monotonic()-started
        rows = { (r["collection"], r["id"]):dict(r) for r in seeds }
        graph_rows = [r.model_dump() for r in graph.chunks]
        scores = {}
        for result in (seeds, graph_rows):
            for rank, row in enumerate(result, 1):
                key = (row["collection"], row["id"])
                if key in rows and rows[key]["text"] != row["text"]:
                    raise KGUnavailable("kg_vector_graph_text_mismatch")
                rows.setdefault(key, row)
                scores[key] = scores.get(key, 0) + 1/(60+rank)
        order = sorted(scores, key=lambda key:(-scores[key], key))
        # Guarantee one graph-supported context when any was found. This is observable,
        # not a claim that every graph candidate is relevant or graph RAG is superior.
        selected = order[:top_k]
        graph_keys = {(r["collection"], r["id"]) for r in graph_rows}
        if graph_rows and not graph_keys.intersection(selected):
            selected = selected[:max(0, top_k-1)] + [(graph_rows[0]["collection"], graph_rows[0]["id"])]
        if len({key[1] for key in selected}) != len(selected):
            raise KGUnavailable("kg_ambiguous_citation_identity")
        reader.publication(pinned["publication_id"])
        diagnostics = graph.diagnostics | dict(policy=POLICY, hybrid_seed_count=len(seeds),
            selected_graph_chunk_count=len(graph_keys.intersection(selected)),
            selected_chunk_count=len(selected), graph_used=bool(graph_keys.intersection(selected)),
            hybrid_seconds=round(hybrid_seconds,3), graph_seconds=round(graph_seconds,3),
            retrieval_status="graph_augmented" if graph_rows else "hybrid_only_no_graph_match")
        diagnostics.update(candidate_count=len(rows),
            candidate_paper_ids=sorted({r["paper_id"] for r in rows.values()}),
            candidate_paper_count=len({r["paper_id"] for r in rows.values()}),
            selected_paper_ids=sorted({rows[key]["paper_id"] for key in selected}),
            selected_paper_count=len({rows[key]["paper_id"] for key in selected}))
        update_span(metadata=diagnostics, output={"chunk_ids":[key[1] for key in selected]})
        return KGContext([rows[key] | dict(score=scores[key]) for key in selected], diagnostics)
    except KGUnavailable:
        raise
    except Exception as error:
        raise KGUnavailable("kg_retrieval_unavailable_or_invalid") from error
    finally:
        if owned:
            reader.close()
