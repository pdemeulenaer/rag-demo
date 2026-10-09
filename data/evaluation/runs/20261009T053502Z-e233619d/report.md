# Evaluation run 20261009T053502Z-e233619d

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `33652665b3231e705348100ca5c1e727886a9d3c97daff7204c8cb560561e14a`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 1 | 102.518 | 0.000 | — | 0 / 1 | — | 0 / 1 | — |

## Judge failures and grounding annotations

Judge errors do not discard completed RAG answers, evidence or retrieval metrics.
Invalid grounding annotations share the existing single retry; unresolved annotations
leave groundedness null/unscored, not a fabricated answer penalty.

- agentic: 1 judge error(s); grounding question IDs needing review: none.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 62.313 | 62.312 | — | — | 20.174 | 20.030 | 102.518 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.000 | — | 0 / 1 | — | — |

## Agentic execution

Mean rounds: `0.0`; mean tool calls: `0.0`; mean evidence chunks: `0.0`; mean planner tokens: `0.0`. Named-paper full coverage: `0.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| planner_failure | 1 |

Synthesis policy counts: `hard_stop`=1.

See `results.json` for per-question answers, evidence, citations and scores.
