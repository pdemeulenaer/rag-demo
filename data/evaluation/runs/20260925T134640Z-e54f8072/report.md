# Evaluation run 20260925T134640Z-e54f8072

Dataset: `9a5fceeaa18570bd7763a34702478ffe7cd235181a4445af9da19cfc6c161327`

Split: `development`; evaluation set: `c3154dae7fe50d34b46058cefb717338dc209ae9dc2446d123358e14306e854a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 1 | 0 | 11.971 | 0.667 | 1.000 | 1.000 | 1.000 |
| hybrid | 1 | 0 | 9.863 | 0.333 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | 1 | 0 | 10.723 | 0.333 | 1.000 | 1.000 | 1.000 |
| agentic | 1 | 0 | 57.459 | 0.667 | 0.000 | 1.000 | 0.500 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 0.667 | 1.000 | 1.000 | 1.000 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 0.333 | 1.000 | 1.000 | 1.000 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 0.333 | 1.000 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 0.667 | 0.000 | 1.000 | 0.500 |

## Agentic execution

Mean rounds: `2.0`; mean tool calls: `9.0`; mean evidence chunks: `15.0`; mean planner tokens: `32585.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| token_budget | 1 |

Synthesis policy counts: `evidence_fallback`=1.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `2.0`; mean selected papers: `1.0`; mean paper-diversity retention: `0.5`. Required-paper recall before/after reranking: `1.0` / `1.0`.

See `results.json` for per-question answers, evidence, citations and scores.
