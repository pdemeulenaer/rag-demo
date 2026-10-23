# Evaluation run 20261022T121120Z-7fead492

Dataset: `3dfe7bf8859748c92238b896dc437487cf5fdef1cd91de3a3f3ca131e1bf8f15`

Split: `development`; evaluation set: `f885b018479f30c00b0ae0f6c05c111557db9313b77d3b9edb83a9e316854fea`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 8 | 0 | 0 | 29.77 | 0.562 | 0.688 | 8 / 0 | 0.938 | 8 / 0 | 0.938 |
| kg | 8 | 0 | 0 | 25.765 | 0.812 | 0.875 | 8 / 0 | 1.000 | 8 / 0 | 1.000 |

## KG coverage

Pinned publication(s): publication:ef340620c8c35358052b02616a177172a1bdc4710641fe603f2fc127b447ba70.
Graph-used runs (policy-defined): 7; Hybrid-only runs: 1.
The reviewed pilot graph covers only part of the corpus; do not attribute Hybrid-only answers to graph retrieval.

Bounded selection runs: 8; actual graph-expansion runs: 7; mean protected Hybrid chunks: 3.0.
Displaced Hybrid chunks: 9; rejected promotion candidates: {"already_in_hybrid_baseline": 3, "no_specific_query_anchor": 3}.
A graph-supported chunk already retrieved by Hybrid is not an actual graph expansion.

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

- hybrid: 1 run(s) flagged during judging; question IDs still needing review: none.
- kg: 0 run(s) flagged during judging; question IDs still needing review: none.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 19.302 | 0.903 | — | 18.389 | 5.324 | 5.141 | 29.77 |
| kg | 17.935 | 0.792 | — | 17.136 | 4.709 | 3.118 | 25.765 |

### Retrieval breakdown (seconds)

Already included in Retrieval above. Embedding includes configured SDK retries;
Qdrant measures query_points calls only, excluding embedding and BM25 encoding.
Repeated/parallel calls are summed, so these work durations can exceed wall time.
Failed calls retain elapsed time; absent stages are not fabricated as zero.

| Mode | Embedding | Qdrant | Graph |
| --- | ---: | ---: | ---: |
| hybrid | 0.589 | 0.299 | — |
| kg | 0.306 | 0.292 | 0.146 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 4 | 0 | 0.375 | 0.625 | 4 / 0 | 1.000 | 1.000 |
| single_fact | 2 | 0 | 0.500 | 0.500 | 2 / 0 | 0.750 | 0.750 |
| single_synthesis | 2 | 0 | 1.000 | 1.000 | 2 / 0 | 1.000 | 1.000 |

## kg by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 4 | 0 | 0.625 | 0.750 | 4 / 0 | 1.000 | 1.000 |
| single_fact | 2 | 0 | 1.000 | 1.000 | 2 / 0 | 1.000 | 1.000 |
| single_synthesis | 2 | 0 | 1.000 | 1.000 | 2 / 0 | 1.000 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
