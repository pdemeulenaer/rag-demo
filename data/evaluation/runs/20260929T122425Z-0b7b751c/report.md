# Evaluation run 20260929T122425Z-0b7b751c

Dataset: `65e2a571824e40e5c843cadf410b772ac7ff679d6fe56804f92f3534f1e28a30`

Split: `development`; evaluation set: `c3154dae7fe50d34b46058cefb717338dc209ae9dc2446d123358e14306e854a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 1 | 0 | 25.352 | 0.667 | 0.500 | 1.000 | 1.000 |
| hybrid | 1 | 0 | 19.683 | 0.333 | 0.500 | 1.000 | 1.000 |
| hybrid_rerank | 1 | 0 | 25.491 | 0.667 | 0.500 | 1.000 | 1.000 |
| agentic | 1 | 0 | 75.885 | 1.000 | 0.500 | 1.000 | 1.000 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 0.667 | 0.500 | 1.000 | 1.000 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 0.333 | 0.500 | 1.000 | 1.000 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 0.667 | 0.500 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 1.000 | 0.500 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `2.0`; mean tool calls: `4.0`; mean evidence chunks: `16.0`; mean planner tokens: `28675.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `2.0`; mean selected papers: `1.0`; mean paper-diversity retention: `0.5`. Required-paper recall before/after reranking: `1.0` / `1.0`.

See `results.json` for per-question answers, evidence, citations and scores.
