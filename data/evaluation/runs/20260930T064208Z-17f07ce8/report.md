# Evaluation run 20260930T064208Z-17f07ce8

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `d45aa3a332a139714a7a432e9fe8269816957f870760f65e952bc349e8528dfa`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 1 | 0 | 4.986 | 0.333 | 0.000 | 0.500 | 0.500 |
| hybrid | 1 | 0 | 4.434 | 0.333 | 0.000 | 1.000 | 0.500 |
| hybrid_rerank | 1 | 0 | 24.536 | 0.667 | 0.500 | 1.000 | 1.000 |
| agentic | 1 | 0 | 58.622 | 0.667 | 0.500 | 1.000 | 1.000 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.333 | 0.000 | 0.500 | 0.500 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.333 | 0.000 | 1.000 | 0.500 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.667 | 0.500 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.667 | 0.500 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `2.0`; mean tool calls: `4.0`; mean evidence chunks: `20.0`; mean planner tokens: `13559.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| token_budget | 1 |

Synthesis policy counts: `evidence_fallback`=1.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `3.0`; mean selected papers: `2.0`; mean paper-diversity retention: `0.6667`. Required-paper recall before/after reranking: `1.0` / `1.0`.

See `results.json` for per-question answers, evidence, citations and scores.
