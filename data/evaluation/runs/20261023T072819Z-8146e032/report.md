# Evaluation run 20261023T072819Z-8146e032

Dataset: `3dfe7bf8859748c92238b896dc437487cf5fdef1cd91de3a3f3ca131e1bf8f15`

Split: `development`; evaluation set: `dd08e0593606573cc74e52c48a211ed223e409cd1d1d1c472229881adf1c3ca5`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 1 | 0 | 0 | 49.63 | 0.500 | 0.500 | 1 / 0 | 1.000 | 1 / 0 | 1.000 |
| kg | 1 | 0 | 0 | 29.803 | 1.000 | 1.000 | 1 / 0 | 1.000 | 1 / 0 | 1.000 |

## KG coverage

Pinned publication(s): publication:ef340620c8c35358052b02616a177172a1bdc4710641fe603f2fc127b447ba70.
Graph-used runs (policy-defined): 1; Hybrid-only runs: 0.
The reviewed pilot graph covers only part of the corpus; do not attribute Hybrid-only answers to graph retrieval.

Bounded selection runs: 1; actual graph-expansion runs: 1; mean protected Hybrid chunks: 3.0.
Displaced Hybrid chunks: 2; rejected promotion candidates: {}.
A graph-supported chunk already retrieved by Hybrid is not an actual graph expansion.
Expansion qualification bases: {"named_paper_fact_overlap": 1, "specific_entity_path": 1}.

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
| hybrid | 33.140 | 1.334 | — | 31.780 | 13.245 | 3.229 | 49.63 |
| kg | 23.021 | 1.139 | — | 21.861 | 4.734 | 2.042 | 29.803 |

### Retrieval breakdown (seconds)

Already included in Retrieval above. Embedding includes configured SDK retries;
Qdrant measures query_points calls only, excluding embedding and BM25 encoding.
Repeated/parallel calls are summed, so these work durations can exceed wall time.
Failed calls retain elapsed time; absent stages are not fabricated as zero.

| Mode | Embedding | Qdrant | Graph |
| --- | ---: | ---: | ---: |
| hybrid | 0.921 | 0.381 | — |
| kg | 0.280 | 0.540 | 0.214 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 1 | 0 | 0.500 | 0.500 | 1 / 0 | 1.000 | 1.000 |

## kg by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 1 | 0 | 1.000 | 1.000 | 1 / 0 | 1.000 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
