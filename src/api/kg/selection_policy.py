"""Bounded evidence diversity for explicit survey/comparison requests, not a planner."""
from .entities import normalized, catalogue_ids
from src.api.rag.modes.named_selection import named_reservations, named_diagnostics


def survey_requested(query):
    # An explicit lexical signal, not semantic complexity classification.
    return bool(set(normalized(query).split()) & {"papers", "studies", "literature", "compare", "comparison"})


def select_context(order, rows, graph_keys, *, limit, query, resolved_ids=(), required_papers=()):
    """Reserve named papers, then graph/survey slots; fill by existing RRF rank.

    Only candidates with literal requested/resolved catalogue IDs in their text
    qualify for survey reservation. This cannot invent missing paper coverage.
    """
    identifiers = catalogue_ids(query) | set(resolved_ids)
    relevant = [key for key in order if identifiers & catalogue_ids(rows[key]["text"])]
    selected = named_reservations(order, rows, required_papers, limit)
    if graph_keys and not graph_keys.intersection(selected) and len(selected) < limit:
        preferred = [key for key in relevant if key in graph_keys] or [key for key in order if key in graph_keys]
        selected.extend(preferred[:1])
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
