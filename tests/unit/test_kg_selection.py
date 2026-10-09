"""Read-only selection logic; no optional library, settings, .env or services."""
from collections import Counter
from uuid import UUID

import pytest

from src.api.kg.contracts import SourceChunk
from src.api.kg.selection import select_chunks, spread


def corpus(papers=3, chunks_per_paper=12):
    chunks = [SourceChunk(paper_id=UUID(int=paper + 1), build_id=UUID(int=paper + 101),
        point_id=UUID(int=1000 + paper * chunks_per_paper + index),
        collection="test", source="arxiv", page_number=index + 1,
        section_header="Results", text="Scientific body text " * 20)
        for paper in range(papers) for index in range(chunks_per_paper)]
    states = {str(chunk.point_id): dict(status="pending", attempts=0) for chunk in chunks}
    return chunks, states


def test_sequential_default_unchanged():
    chunks, states = corpus()
    states[str(chunks[0].point_id)] = dict(status="complete", attempts=1)
    states[str(chunks[1].point_id)] = dict(status="failed", attempts=1)
    assert select_chunks(chunks, states, max_calls=3) == chunks[2:5]
    assert select_chunks(chunks, states, max_calls=3, retry_failed=True) == chunks[1:4]
    assert select_chunks(chunks, states, max_calls=3, failed_only=True) == chunks[1:2]


def test_sampling_distributed_and_deterministic():
    chunks, states = corpus()
    sample = select_chunks(chunks, states, max_calls=9, chunks_per_paper=3)
    assert Counter(chunk.paper_id for chunk in sample) == {UUID(int=i): 3 for i in (1, 2, 3)}
    assert sample == select_chunks(chunks, states, max_calls=9, chunks_per_paper=3)
    assert [chunk.page_number for chunk in sample[:3]] == [3, 3, 3]
    assert [chunk.page_number for chunk in sample[3:6]] == [7, 7, 7]
    assert [chunk.page_number for chunk in sample[6:]] == [11, 11, 11]


def test_prior_attempts_cap_sample_including_failures():
    chunks, states = corpus()
    for i in range(5):
        states[str(chunks[i].point_id)] = dict(status="failed" if i == 0 else "complete", attempts=1)
    sample = select_chunks(chunks, states, max_calls=9, chunks_per_paper=3)
    assert len(sample) == 6 and all(chunk.paper_id != UUID(int=1) for chunk in sample)
    for chunk in sample:
        states[str(chunk.point_id)] = dict(status="complete", attempts=1)
    assert select_chunks(chunks, states, max_calls=9, chunks_per_paper=3) == []


def test_small_global_cap_is_fair_across_resumption():
    chunks, states = corpus(papers=7)
    sampled_papers = set()
    for _ in range(7):
        sample = select_chunks(chunks, states, max_calls=1, chunks_per_paper=3)
        assert len(sample) == 1
        sampled_papers.add(sample[0].paper_id)
        states[str(sample[0].point_id)] = dict(status="complete", attempts=1)
    assert len(sampled_papers) == 7


def test_body_preference_with_short_paper_fallback():
    chunks, states = corpus(papers=1, chunks_per_paper=3)
    chunks[0] = chunks[0].model_copy(update=dict(section_header="Abstract"))
    chunks[2] = chunks[2].model_copy(update=dict(section_header="References"))
    assert select_chunks(chunks, states, max_calls=1, chunks_per_paper=1) == [chunks[1]]
    assert len(select_chunks(chunks, states, max_calls=5, chunks_per_paper=5)) == 3


@pytest.mark.parametrize("kwargs", [dict(max_calls=0), dict(max_calls=1001),
    dict(max_calls=3, chunks_per_paper=0), dict(max_calls=3, chunks_per_paper=1001),
    dict(max_calls=3, chunks_per_paper=2, retry_failed=True),
    dict(max_calls=3, chunks_per_paper=2, failed_only=True)])
def test_invalid_selection_fails_before_provider_use(kwargs):
    chunks, states = corpus()
    with pytest.raises(ValueError):
        select_chunks(chunks, states, **kwargs)


def test_failed_only_does_not_mix_pending_or_completed():
    chunks, states = corpus()
    for index, status in ((1, "failed"), (4, "interrupted"), (8, "complete")):
        states[str(chunks[index].point_id)] = dict(status=status, attempts=1)
    assert select_chunks(chunks, states, max_calls=10, failed_only=True) == [chunks[1], chunks[4]]


def test_spread_handles_empty_and_sparse_groups():
    assert spread([], 3) == []
    assert spread([1], 5) == [1]
    assert spread([1, 2], 0) == []
