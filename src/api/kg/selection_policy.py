"""Deterministic bounded KG selection. No models, inferred aliases or gold labels."""
from .entities import normalized, catalogue_ids
from .fact_matching import MIN_FACT_TERMS
from src.api.rag.modes.named_selection import named_reservations, named_diagnostics

SELECTION_POLICY = "protected-hybrid-bounded-graph-v2"
MAX_GRAPH_EXPANSIONS = 2

def survey_requested(query):
    # An explicit lexical signal, not semantic complexity classification.
    return bool(set(normalized(query).split()) & {"papers", "studies", "literature", "compare", "comparison"})


def select_context(order, rows, *, limit, query, resolved_ids=(), required_papers=()):
    """Bound the reader's source candidates with literal-ID survey diversity.

    Only candidates with literal requested/resolved catalogue IDs in their text
    qualify for survey reservation. This cannot invent missing paper coverage.
    """
    identifiers = catalogue_ids(query) | set(resolved_ids)
    relevant = [key for key in order if identifiers & catalogue_ids(rows[key]["text"])]
    selected = named_reservations(order, rows, required_papers, limit)
    seen = {rows[key]["paper_id"] for key in selected}
    if survey_requested(query):
        for key in relevant:
            if len(selected) >= limit:
                break
            if rows[key]["paper_id"] not in seen:
                selected.append(key)
                seen.add(rows[key]["paper_id"])
    for key in order:
        if len(selected) >= limit:
            break
        if key not in selected:
            selected.append(key)
    chosen = set(selected)
    selected = [key for key in order if key in chosen]
    return selected, dict(survey_coverage_requested=survey_requested(query),
        coverage_candidate_paper_ids=sorted({rows[k]["paper_id"] for k in relevant}),
        coverage_selected_paper_ids=sorted({rows[k]["paper_id"] for k in selected if k in relevant}),
        paper_diversity_applied=set(selected) != set(order[:limit]),
        **named_diagnostics(order, rows, selected, required_papers))


def select_expansion_context(order, rows, graph_keys, *, hybrid_order, graph_support,
                             limit, query, resolved_ids=(), required_papers=()):
    """Protect Hybrid's head; admit at most two specifically anchored graph additions.

    Default k=5 protects three Hybrid passages. Smaller k protects at least half;
    named-paper reservations take precedence, potentially leaving no expansion room.
    Graph passages already in the Hybrid baseline do not consume expansion slots.
    """
    hybrid_order = list(dict.fromkeys(hybrid_order))
    baseline_set = set(named_reservations(hybrid_order, rows, required_papers, limit))
    for key in hybrid_order:
        if len(baseline_set) >= limit:
            break
        baseline_set.add(key)
    baseline = [key for key in hybrid_order if key in baseline_set]
    protected = set(named_reservations(baseline, rows, required_papers, limit))
    expansion_budget = min(MAX_GRAPH_EXPANSIONS, max(1, limit // 2))
    protected_target = max(1, limit - expansion_budget)
    for key in baseline:
        if len(protected) >= protected_target:
            break
        protected.add(key)
    expansion_limit = min(expansion_budget, limit-len(protected))
    requested = {(p.collection, p.build_id) for p in required_papers}
    support = {(r["collection"], r["id"]): r for r in graph_support}
    promoted, decisions = [], []
    positions = {key: index for index, key in enumerate(order)}
    graph_order = sorted((k for k in order if k in graph_keys), key=lambda key: (
        0 if support.get(key, {}).get("fact_record_id") and
        len(support[key].get("matched_fact_terms", [])) >= MIN_FACT_TERMS else 1,
        -len(support.get(key, {}).get("matched_fact_terms", [])), positions[key]))
    for key in graph_order:
        row = rows[key]
        witness = support.get(key, {})
        anchors = sorted(witness.get("anchor_record_ids", []))
        fact_terms = sorted(set(witness.get("matched_fact_terms", [])))
        in_scope = not requested or (row.get("collection"), row.get("build_id")) in requested
        fact_match = bool(requested and witness.get("fact_record_id") and len(fact_terms) >= MIN_FACT_TERMS)
        qualified = in_scope and (bool(anchors) or fact_match)
        if not in_scope:
            reason = "outside_requested_papers"
        elif key in baseline_set:
            reason = "already_in_hybrid_baseline"
        elif not qualified:
            reason = "no_named_fact_or_entity_match" if requested else "no_specific_query_anchor"
        elif len(promoted) >= expansion_limit:
            reason = "expansion_capacity_exhausted"
        else:
            promoted.append(key)
            reason = "qualified_graph_expansion"
        decisions.append(dict(collection=key[0], id=key[1], build_id=row.get("build_id"),
            qualified=qualified, reason=reason, anchor_record_ids=anchors,
            qualification_basis="named_paper_fact_overlap" if in_scope and fact_match else
                "specific_entity_path" if in_scope and anchors else None,
            fact_record_id=witness.get("fact_record_id"), fact_record_kind=witness.get("fact_record_kind"),
            matched_fact_terms=fact_terms))
    selected = [key for key in baseline if key in protected] + promoted
    for key in baseline:
        if len(selected) >= limit:
            break
        if key not in selected:
            selected.append(key)
    if not promoted:
        # A no-promotion result must preserve the baseline order too, including
        # named reservations near its tail; provenance alone cannot reshuffle it.
        selected = list(baseline)
    chosen = set(selected)
    for decision in decisions:
        key = (decision["collection"], decision["id"])
        decision["selected"] = key in chosen
        decision["selection_role"] = ("protected_hybrid" if key in protected else
            "graph_expansion" if key in promoted else "hybrid_fill" if key in chosen else "rejected")
    def refs(keys):
        return [dict(collection=key[0], id=key[1]) for key in keys]

    identifiers = catalogue_ids(query) | set(resolved_ids)
    relevant = [key for key in order if identifiers & catalogue_ids(rows[key]["text"])]
    diagnostics = dict(selection_policy=SELECTION_POLICY,
        hybrid_baseline_chunks=refs(baseline), protected_hybrid_chunks=refs(k for k in baseline if k in protected),
        hybrid_protected_count=len(protected), graph_expansion_limit=expansion_limit,
        graph_expansion_count=len(promoted), graph_expansion_chunks=refs(promoted),
        displaced_hybrid_chunks=refs(k for k in baseline if k not in chosen),
        graph_candidate_decisions=decisions,
        graph_rejected_candidate_count=sum(not d["qualified"] for d in decisions),
        survey_coverage_requested=survey_requested(query),
        coverage_candidate_paper_ids=sorted({rows[k]["paper_id"] for k in relevant}),
        coverage_selected_paper_ids=sorted({rows[k]["paper_id"] for k in selected if k in relevant}),
        paper_diversity_applied=baseline != hybrid_order[:limit],
        **named_diagnostics(order, rows, selected, required_papers))
    return selected, diagnostics
