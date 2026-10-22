# Evaluation run 20261021T053945Z-2b96ce50

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `3ff7dbe386b47d405022ebf7998c111c73a082b2bc6829e48f82c91aaa12f2d3`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 33 | 0 | 0 | 33.658 | 0.543 | 0.818 | 33 / 0 | 0.970 | 33 / 0 | 0.985 |
| kg | 33 | 1 | 0 | 31.093 | 0.549 | 0.839 | 31 / 2 | 0.953 | 32 / 1 | 0.984 |

## KG coverage

Pinned publication(s): publication:ef340620c8c35358052b02616a177172a1bdc4710641fe603f2fc127b447ba70.
Graph-supported runs: 8; Hybrid-only runs: 24.
The reviewed pilot graph covers only part of the corpus; do not attribute Hybrid-only answers to graph retrieval.

## KG retrieval failures

Failed retrievals: 1; codes: {"kg_retrieval_unavailable_or_invalid": 1}; stages: {"hybrid_search": 1}.
Failed retrievals have no answer-quality scores; inspect successful sample counts before comparing modes.

## Judge failures and grounding annotations

Judge errors do not discard completed RAG answers, evidence or retrieval metrics.
Invalid grounding annotations share the existing single retry; unresolved annotations
leave groundedness null/unscored, not a fabricated answer penalty.

- hybrid: 0 judge error(s); grounding question IDs needing review: none.
- kg: 0 judge error(s); grounding question IDs needing review: none.

## Judge consistency

Unresolved reference correctness is null/unscored, not zero or a promoted score.
Means use scored samples only; compare scored/unscored counts before comparing modes.
Unresolved contradictions/source ambiguities need manual review, not a conclusion of poor RAG quality.
A clean check means no detected conflict, not proof of semantic correctness.

- hybrid: 2 run(s) flagged during judging; question IDs still needing review: none.
- kg: 4 run(s) flagged during judging; question IDs still needing review: q0060.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 23.542 | 0.784 | — | 22.742 | 6.699 | 3.414 | 33.658 |
| kg | 21.434 | 0.886 | — | 21.035 | 7.232 | 2.726 | 31.093 |

### Retrieval breakdown (seconds)

Already included in Retrieval above. Embedding includes configured SDK retries;
Qdrant measures query_points calls only, excluding embedding and BM25 encoding.
Repeated/parallel calls are summed, so these work durations can exceed wall time.
Failed calls retain elapsed time; absent stages are not fabricated as zero.

| Mode | Embedding | Qdrant | Graph |
| --- | ---: | ---: | ---: |
| hybrid | 0.412 | 0.349 | — |
| kg | 0.370 | 0.487 | 0.130 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.283 | 0.800 | 5 / 0 | 1.000 | 1.000 |
| cross_multihop | 5 | 0 | 0.317 | 0.500 | 5 / 0 | 0.800 | 0.900 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1 / 0 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.756 | 0.962 | 13 / 0 | 1.000 | 1.000 |
| single_synthesis | 9 | 0 | 0.565 | 0.778 | 9 / 0 | 1.000 | 1.000 |

## kg by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.283 | 0.800 | 5 / 0 | 0.900 | 1.000 |
| cross_multihop | 5 | 0 | 0.317 | 0.500 | 5 / 0 | 0.800 | 0.900 |
| metadata_discovery | 1 | 0 | 0.000 | — | 0 / 1 | 1.000 | 1.000 |
| single_fact | 13 | 1 | 0.819 | 1.000 | 12 / 1 | 1.000 | 1.000 |
| single_synthesis | 9 | 0 | 0.528 | 0.833 | 9 / 0 | 1.000 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
