# Evaluation run 20260925T134817Z-80414224

Dataset: `9a5fceeaa18570bd7763a34702478ffe7cd235181a4445af9da19cfc6c161327`

Split: `development`; evaluation set: `d45aa3a332a139714a7a432e9fe8269816957f870760f65e952bc349e8528dfa`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 1 | 0 | 3.934 | 0.333 | 0.000 | 1.000 | 0.500 |
| hybrid | 1 | 0 | 3.601 | 0.333 | 0.000 | 1.000 | 0.500 |
| hybrid_rerank | 1 | 0 | 13.569 | 0.333 | 0.500 | 1.000 | 1.000 |
| agentic | 1 | 0 | 99.146 | 0.667 | 0.000 | 0.500 | 0.500 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.333 | 0.000 | 1.000 | 0.500 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.333 | 0.000 | 1.000 | 0.500 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.333 | 0.500 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.667 | 0.000 | 0.500 | 0.500 |

## Agentic execution

Mean rounds: `1.0`; mean tool calls: `4.0`; mean evidence chunks: `16.0`; mean planner tokens: `15928.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `4.0`; mean selected papers: `2.0`; mean paper-diversity retention: `0.5`. Required-paper recall before/after reranking: `1.0` / `1.0`.

See `results.json` for per-question answers, evidence, citations and scores.
