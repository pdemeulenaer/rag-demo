"""Deterministic, checkpoint-aware extraction sampling; no services or model calls."""
from collections import defaultdict
import re


def spread(items, count):
    """Pick bin midpoints rather than always extracting the start of a document."""
    count = min(count, len(items))
    return [items[((2 * i + 1) * len(items)) // (2 * count)] for i in range(count)]


def body_chunk(chunk):
    """Prefer substantial body sections; this heuristic is not scientific review."""
    leaf = (chunk.section_header or "").split(" > ")[-1]
    leaf = re.sub(r"[*#_`]+", "", leaf).strip().casefold()
    metadata = re.match(r"^(?:\d+[.\s]*)?(abstract|resumen|references|bibliography|acknowledg)", leaf)
    text = "\n".join(line for line in chunk.text.splitlines() if not line.lstrip().startswith("#"))
    return bool(leaf and not metadata and len(text.split()) >= 40
                and not re.search(r"\*?\*?Keywords:\*?\*?", text, re.IGNORECASE))


def select_chunks(chunks, states, *, max_calls, chunks_per_paper=None,
                  retry_failed=False, failed_only=False):
    """Sampling caps distinct attempted chunks per paper over the directory's lifetime.

    Failed attempts count towards that cap; explicit retries are a separate mode.
    Sequential extraction remains the default. All modes retain the global call cap.
    """
    if not 1 <= max_calls <= 1000:
        raise ValueError("Per-invocation call limit must be 1–1000")
    if chunks_per_paper is not None:
        if not 1 <= chunks_per_paper <= 1000:
            raise ValueError("Chunks-per-paper sampling limit must be 1–1000")
        if retry_failed or failed_only:
            raise ValueError("Sampling selects new pending chunks; omit sampling when explicitly retrying failures")
    allowed = {"failed", "interrupted"} if failed_only else {"pending"}
    if retry_failed:
        allowed |= {"failed", "interrupted"}
    eligible = [chunk for chunk in chunks
                if states[str(chunk.point_id)]["status"] in allowed]
    if chunks_per_paper is None:
        return eligible[:max_calls]
    attempted = defaultdict(int)
    for chunk in chunks:
        if states[str(chunk.point_id)]["attempts"] > 0:
            attempted[chunk.paper_id] += 1
    groups = defaultdict(list)
    for chunk in eligible:
        groups[chunk.paper_id].append(chunk)
    samples = []
    # Less-sampled papers go first, keeping small global caps from starving later papers.
    for paper_id in sorted(groups, key=lambda key: attempted[key]):
        quota = chunks_per_paper - attempted[paper_id]
        if quota <= 0:
            continue
        group = groups[paper_id]
        body = [chunk for chunk in group if body_chunk(chunk)]
        preferred = spread(body, quota)
        selected_ids = {chunk.point_id for chunk in preferred}
        fallback = [chunk for chunk in group if chunk.point_id not in selected_ids]
        selected = preferred + spread(fallback, max(0, quota - len(preferred)))
        order = {chunk.point_id: index for index, chunk in enumerate(group)}
        samples.append(sorted(selected, key=lambda chunk: order[chunk.point_id]))
    return [sample[round_index] for round_index in range(chunks_per_paper)
            for sample in samples if round_index < len(sample)][:max_calls]
