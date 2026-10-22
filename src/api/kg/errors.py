"""Static public KG failure codes; never serialize raw database/provider errors."""


PUBLIC_CODES = frozenset({
    "kg_no_active_publication", "kg_publication_changed", "kg_invalid_publication",
    "kg_query_record_limit", "kg_invalid_source_builds", "kg_query_source_link_limit",
    "kg_query_text_limit", "kg_traversal_scope_violation", "kg_source_scope_changed",
    "kg_invalid_record", "kg_missing_record_dependency", "kg_invalid_relationship_role",
    "kg_source_scope_violation", "kg_invalid_source_provenance", "kg_conflicting_source_text",
    "kg_incomplete_record_provenance", "kg_explicit_catalogue_scope_required",
    "kg_vector_graph_text_mismatch", "kg_ambiguous_citation_identity",
    "kg_retrieval_unavailable_or_invalid", "kg_database_unavailable_or_invalid",
    "kg_close_failed",
})
PUBLIC_STAGES = frozenset({"configuration", "connect", "pin", "hybrid_search", "graph_search",
                           "merge", "selection", "recheck", "close"})


class KGUnavailable(ValueError):
    """Application-owned code and stage, independent of arbitrary exception messages."""

    def __init__(self, code, *, stage=None):
        self.code = code if code in PUBLIC_CODES else "kg_retrieval_unavailable_or_invalid"
        self.stage = stage if stage in PUBLIC_STAGES else None
        super().__init__(self.code)

    @property
    def safe_diagnostics(self):
        return {"code": self.code, **({"stage": self.stage} if self.stage else {})}
