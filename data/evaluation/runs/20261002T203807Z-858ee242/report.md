# Evaluation run 20261002T203807Z-858ee242

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `33652665b3231e705348100ca5c1e727886a9d3c97daff7204c8cb560561e14a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 8.932 | 0.000 | 0.000 | 1.000 | 0.500 |

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 5.089 | 5.088 | — | — | 2.521 | 1.321 | 8.932 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.000 | 0.000 | 1.000 | 0.500 |

## Agentic execution

Mean rounds: `0.0`; mean tool calls: `0.0`; mean evidence chunks: `0.0`; mean planner tokens: `1825.0`. Named-paper full coverage: `None` across `0` detected runs.

| Stop reason | Runs |
| --- | ---: |
| planner_failure | 1 |

Synthesis policy counts: `hard_stop`=1.

See `results.json` for per-question answers, evidence, citations and scores.
