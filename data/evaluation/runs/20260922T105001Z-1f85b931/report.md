# Evaluation run 20260922T105001Z-1f85b931

Dataset: `c0cd09df44294628e866781056b8606a97e8db1c80b612bfdf6d512a366a87a4`

Split: `development`; evaluation set: `d45aa3a332a139714a7a432e9fe8269816957f870760f65e952bc349e8528dfa`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 1 | 0 | 6.931 | 0.333 | — | — | — |
| hybrid_rerank | 1 | 0 | 4.794 | 0.333 | — | — | — |
| agentic | 1 | 0 | 12.535 | 0.667 | — | — | — |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.333 | — | — | — |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.333 | — | — | — |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.667 | — | — | — |

## Agentic execution

Mean rounds: `1.0`; mean tool calls: `2.0`; mean evidence chunks: `16.0`; mean planner tokens: `9010.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| token_budget | 1 |

Synthesis policy counts: `evidence_fallback`=1.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `4.0`; mean selected papers: `1.0`; mean paper-diversity retention: `0.25`. Required-paper recall before/after reranking: `1.0` / `0.5`.

See `results.json` for per-question answers, evidence, citations and scores.
