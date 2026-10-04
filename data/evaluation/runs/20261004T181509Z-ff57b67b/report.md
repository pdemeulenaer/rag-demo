# Evaluation run 20261004T181509Z-ff57b67b

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `33652665b3231e705348100ca5c1e727886a9d3c97daff7204c8cb560561e14a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 177.392 | 0.500 | 1.000 | 1.000 | 1.000 |

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 170.498 | 23.986 | — | 146.505 | 2.456 | 4.438 | 177.392 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.500 | 1.000 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `1.0`; mean tool calls: `2.0`; mean evidence chunks: `16.0`; mean planner tokens: `12757.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

See `results.json` for per-question answers, evidence, citations and scores.
