# Evaluation run 20261007T092753Z-8c886f5f

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `33652665b3231e705348100ca5c1e727886a9d3c97daff7204c8cb560561e14a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 15.125 | 0.000 | 0.000 | 1 / 0 | 0.500 | 0.500 |

## Judge consistency

Unresolved reference correctness is null/unscored, not zero or a promoted score.
Means use scored samples only; compare scored/unscored counts before comparing modes.
Unresolved contradictions/source ambiguities need manual review, not a conclusion of poor RAG quality.
A clean check means no detected conflict, not proof of semantic correctness.

- agentic: 0 run(s) flagged during judging; question IDs still needing review: none.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 7.811 | 7.811 | — | — | 5.566 | 1.744 | 15.125 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.000 | 0.000 | 1 / 0 | 0.500 | 0.500 |

## Agentic execution

Mean rounds: `0.0`; mean tool calls: `0.0`; mean evidence chunks: `0.0`; mean planner tokens: `3370.0`. Named-paper full coverage: `0.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| planner_failure | 1 |

Synthesis policy counts: `hard_stop`=1.

See `results.json` for per-question answers, evidence, citations and scores.
