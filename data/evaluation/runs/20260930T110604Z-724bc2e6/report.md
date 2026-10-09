# Evaluation run 20260930T110604Z-724bc2e6

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `33652665b3231e705348100ca5c1e727886a9d3c97daff7204c8cb560561e14a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 1 | 0 | 14.762 | 0.000 | 0.000 | 1.000 | 0.500 |
| hybrid | 1 | 0 | 20.859 | 0.250 | 0.000 | 0.500 | 0.500 |
| hybrid_rerank | 1 | 0 | 16.421 | 0.250 | 0.000 | 1.000 | 0.500 |
| agentic | 1 | 0 | 173.081 | 0.250 | 0.500 | 1.000 | 1.000 |

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 11.061 | 1.870 | — | 9.181 | 2.267 | 1.433 | 14.762 |
| hybrid | 15.087 | 0.316 | — | 14.761 | 2.192 | 3.580 | 20.859 |
| hybrid_rerank | 12.784 | 0.624 | 0.318 | 12.147 | 2.612 | 1.024 | 16.421 |
| agentic | 168.798 | 11.723 | — | 157.068 | 1.977 | 2.306 | 173.081 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.000 | 0.000 | 1.000 | 0.500 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.250 | 0.000 | 0.500 | 0.500 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.250 | 0.000 | 1.000 | 0.500 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.250 | 0.500 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `2.0`; mean tool calls: `5.0`; mean evidence chunks: `32.0`; mean planner tokens: `12561.0`. Named-paper full coverage: `None` across `0` detected runs.

| Stop reason | Runs |
| --- | ---: |
| token_budget | 1 |

Synthesis policy counts: `evidence_fallback`=1.
Planner preflight stopped 1 run(s); mean spent-plus-estimated-next-call tokens: `30253.0` (conservative estimate, not billed usage).

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `2.0`; mean selected papers: `1.0`; mean paper-diversity retention: `0.5`. Required-paper recall before/after reranking: `1.0` / `0.5`.

See `results.json` for per-question answers, evidence, citations and scores.
