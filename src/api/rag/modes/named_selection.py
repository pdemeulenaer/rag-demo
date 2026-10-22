"""One-shot diversity for catalogue-resolved quoted paper titles, never gold labels."""


class SelectedContext(list):
    def __init__(self, rows, diagnostics):
        super().__init__(rows)
        self.diagnostics = diagnostics


def named_reservations(order, rows, required_papers, limit):
    """Reserve the highest-ranked present chunk per exact collection/build pair."""
    reserved = []
    for paper in required_papers:
        key = next((key for key in order if rows[key].get("build_id") == paper.build_id
                    and rows[key].get("collection") == paper.collection), None)
        if key is not None and key not in reserved and len(reserved) < limit:
            reserved.append(key)
    return reserved


def named_diagnostics(order, rows, selected, required_papers):
    present = {(rows[key].get("collection"), rows[key].get("build_id")) for key in order}
    covered = {(rows[key].get("collection"), rows[key].get("build_id")) for key in selected}
    return dict(
        named_required_build_ids=[p.build_id for p in required_papers],
        named_candidate_missing_build_ids=[p.build_id for p in required_papers
                                          if (p.collection, p.build_id) not in present],
        named_selected_missing_build_ids=[p.build_id for p in required_papers
                                         if (p.collection, p.build_id) not in covered],
    )


def select_named_context(candidates, required_papers, limit):
    order = list(dict.fromkeys((r.get("collection"), r["id"]) for r in candidates))
    rows = {(r.get("collection"), r["id"]): r for r in candidates}
    reserved = named_reservations(order, rows, required_papers, limit)
    chosen = set(reserved)
    for key in order:
        if len(chosen) >= limit:
            break
        chosen.add(key)
    selected = [key for key in order if key in chosen]
    candidate_papers = sorted({r["paper_id"] for r in candidates if r.get("paper_id")})
    selected_papers = sorted({rows[k]["paper_id"] for k in selected if rows[k].get("paper_id")})
    return SelectedContext([rows[k] for k in selected], dict(
        candidate_count=len(order), candidate_paper_ids=candidate_papers,
        candidate_paper_count=len(candidate_papers), selected_paper_ids=selected_papers,
        selected_paper_count=len(selected_papers), selected_count=len(selected),
        named_paper_diversity_guard_applied=selected != order[:limit],
        reserved_candidate_ids=[k[1] for k in reserved],
        **named_diagnostics(order, rows, selected, required_papers),
    ))
