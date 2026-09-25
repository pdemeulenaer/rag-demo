# Evaluation run 20260922T120439Z-39e74e1c

Dataset: `c44a47c2c0e5609eebead972c8ef04f028a51ae9abc5c58a0ef1581b340b3930`

Split: `development`; evaluation set: `d45aa3a332a139714a7a432e9fe8269816957f870760f65e952bc349e8528dfa`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 1 | 0 | 16.363 | 0.333 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | 1 | 0 | 14.271 | 0.333 | 0.500 | 1.000 | 1.000 |
| agentic | 1 | 0 | 28.241 | 0.667 | 1.000 | 1.000 | 1.000 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.333 | 1.000 | 1.000 | 1.000 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.333 | 0.500 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.667 | 1.000 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `1.0`; mean tool calls: `4.0`; mean evidence chunks: `16.0`; mean planner tokens: `12186.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `3.0`; mean selected papers: `2.0`; mean paper-diversity retention: `0.6667`. Required-paper recall before/after reranking: `1.0` / `1.0`.

See `results.json` for per-question answers, evidence, citations and scores.
