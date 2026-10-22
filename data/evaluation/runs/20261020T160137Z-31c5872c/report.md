# Evaluation run 20261020T160137Z-31c5872c

Dataset: `3dfe7bf8859748c92238b896dc437487cf5fdef1cd91de3a3f3ca131e1bf8f15`

Split: `development`; evaluation set: `f885b018479f30c00b0ae0f6c05c111557db9313b77d3b9edb83a9e316854fea`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 8 | 0 | 0 | 36.464 | 0.562 | 0.625 | 8 / 0 | 0.938 | 8 / 0 | 1.000 |
| kg | 8 | 0 | 0 | 30.841 | 1.000 | 0.938 | 8 / 0 | 1.000 | 8 / 0 | 1.000 |

## KG coverage

Pinned publication(s): publication:ef340620c8c35358052b02616a177172a1bdc4710641fe603f2fc127b447ba70.
Graph-supported runs: 8; Hybrid-only runs: 0.
The reviewed pilot graph covers only part of the corpus; do not attribute Hybrid-only answers to graph retrieval.

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
- kg: 0 run(s) flagged during judging; question IDs still needing review: none.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 25.104 | 0.751 | — | 24.343 | 8.111 | 3.244 | 36.464 |
| kg | 22.065 | 0.724 | — | 21.335 | 5.567 | 3.206 | 30.841 |

### Retrieval breakdown (seconds)

Already included in Retrieval above. Embedding includes configured SDK retries;
Qdrant measures query_points calls only, excluding embedding and BM25 encoding.
Repeated/parallel calls are summed, so these work durations can exceed wall time.
Failed calls retain elapsed time; absent stages are not fabricated as zero.

| Mode | Embedding | Qdrant | Graph |
| --- | ---: | ---: | ---: |
| hybrid | 0.488 | 0.248 | — |
| kg | 0.312 | 0.251 | 0.116 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 4 | 0 | 0.375 | 0.500 | 4 / 0 | 1.000 | 1.000 |
| single_fact | 2 | 0 | 0.500 | 0.500 | 2 / 0 | 0.750 | 1.000 |
| single_synthesis | 2 | 0 | 1.000 | 1.000 | 2 / 0 | 1.000 | 1.000 |

## kg by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 4 | 0 | 1.000 | 1.000 | 4 / 0 | 1.000 | 1.000 |
| single_fact | 2 | 0 | 1.000 | 0.750 | 2 / 0 | 1.000 | 1.000 |
| single_synthesis | 2 | 0 | 1.000 | 1.000 | 2 / 0 | 1.000 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
