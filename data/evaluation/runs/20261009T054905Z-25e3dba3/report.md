# Evaluation run 20261009T054905Z-25e3dba3

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `3ff7dbe386b47d405022ebf7998c111c73a082b2bc6829e48f82c91aaa12f2d3`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 33 | 0 | 0 | 17.19 | 0.495 | 0.667 | 33 / 0 | 0.955 | 33 / 0 | 0.909 |
| hybrid | 33 | 0 | 0 | 18.78 | 0.558 | 0.758 | 33 / 0 | 0.939 | 33 / 0 | 0.894 |
| hybrid_rerank | 33 | 0 | 0 | 20.631 | 0.497 | 0.774 | 31 / 2 | 0.985 | 33 / 0 | 0.970 |
| agentic | 33 | 0 | 1 | 50.605 | 0.631 | 0.850 | 30 / 3 | 0.984 | 32 / 1 | 0.970 |

## Judge failures and grounding annotations

Judge errors do not discard completed RAG answers, evidence or retrieval metrics.
Invalid grounding annotations share the existing single retry; unresolved annotations
leave groundedness null/unscored, not a fabricated answer penalty.

- vanilla: 0 judge error(s); grounding question IDs needing review: none.
- hybrid: 0 judge error(s); grounding question IDs needing review: none.
- hybrid_rerank: 0 judge error(s); grounding question IDs needing review: none.
- agentic: 1 judge error(s); grounding question IDs needing review: none.

## Judge consistency

Unresolved reference correctness is null/unscored, not zero or a promoted score.
Means use scored samples only; compare scored/unscored counts before comparing modes.
Unresolved contradictions/source ambiguities need manual review, not a conclusion of poor RAG quality.
A clean check means no detected conflict, not proof of semantic correctness.

- vanilla: 1 run(s) flagged during judging; question IDs still needing review: none.
- hybrid: 0 run(s) flagged during judging; question IDs still needing review: none.
- hybrid_rerank: 6 run(s) flagged during judging; question IDs still needing review: q0038, q0052.
- agentic: 6 run(s) flagged during judging; question IDs still needing review: q0028, q0038, q0046.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 11.438 | 0.705 | — | 13.613 | 3.784 | 1.967 | 17.19 |
| hybrid | 12.909 | 0.665 | — | 13.923 | 3.773 | 2.095 | 18.78 |
| hybrid_rerank | 14.116 | 1.303 | 0.617 | 12.805 | 4.373 | 2.140 | 20.631 |
| agentic | 26.064 | 9.215 | — | 16.841 | 4.353 | 20.186 | 50.605 |

### Agentic synthesis breakdown (seconds)

These sub-stages are already included in Generation above. Review combines
both attempts. Means cover measured runs only; repair means exclude runs
without repair (see sample_counts in summary.json).

| Mode | Draft | Review(s) | Repair (when run) |
| --- | ---: | ---: | ---: |
| agentic | 5.784 | 9.642 | 4.127 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.167 | 0.200 | 5 / 0 | 0.900 | 0.800 |
| cross_multihop | 5 | 0 | 0.317 | 0.200 | 5 / 0 | 0.800 | 0.600 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1 / 0 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.731 | 0.923 | 13 / 0 | 1.000 | 1.000 |
| single_synthesis | 9 | 0 | 0.491 | 0.833 | 9 / 0 | 1.000 | 1.000 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.317 | 0.700 | 5 / 0 | 1.000 | 0.900 |
| cross_multihop | 5 | 0 | 0.317 | 0.200 | 5 / 0 | 0.700 | 0.600 |
| metadata_discovery | 1 | 0 | 0.000 | 0.000 | 1 / 0 | 0.500 | 0.500 |
| single_fact | 13 | 0 | 0.756 | 0.962 | 13 / 0 | 1.000 | 0.962 |
| single_synthesis | 9 | 0 | 0.602 | 0.889 | 9 / 0 | 1.000 | 1.000 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.100 | 0.625 | 4 / 1 | 1.000 | 1.000 |
| cross_multihop | 5 | 0 | 0.333 | 0.250 | 4 / 1 | 0.900 | 0.800 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1 / 0 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.679 | 0.962 | 13 / 0 | 1.000 | 1.000 |
| single_synthesis | 9 | 0 | 0.602 | 0.778 | 9 / 0 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.500 | 0.875 | 4 / 1 | 1.000 | 1.000 |
| cross_multihop | 5 | 0 | 0.433 | 1.000 | 4 / 1 | 1.000 | 1.000 |
| metadata_discovery | 1 | 0 | 0.000 | 0.000 | 1 / 0 | 0.500 | 0.500 |
| single_fact | 13 | 0 | 0.782 | 0.923 | 13 / 0 | 1.000 | 0.962 |
| single_synthesis | 9 | 0 | 0.667 | 0.750 | 8 / 1 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `1.515`; mean tool calls: `2.848`; mean evidence chunks: `14.273`; mean planner tokens: `13578.818`. Named-paper full coverage: `1.0` across `30` detected runs.

| Stop reason | Runs |
| --- | ---: |
| no_progress | 1 |
| planner_failure | 1 |
| sufficient | 20 |
| token_budget | 11 |

Synthesis policy counts: `evidence_fallback`=13, `model_finish`=20.
Planner preflight stopped 11 run(s); mean spent-plus-estimated-next-call tokens: `26311.091` (conservative estimate, not billed usage).
Planner context was compacted in 4 run(s), preserving original evidence and token limits.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `3.091`; mean selected papers: `1.273`; mean paper-diversity retention: `0.5829`. Required-paper recall before/after reranking: `1.0` / `0.9848`.

See `results.json` for per-question answers, evidence, citations and scores.
