# Evaluation run 20260929T081208Z-82f11ea8

Dataset: `65e2a571824e40e5c843cadf410b772ac7ff679d6fe56804f92f3534f1e28a30`

Split: `development`; evaluation set: `c3154dae7fe50d34b46058cefb717338dc209ae9dc2446d123358e14306e854a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 40.71 | 1.000 | 0.500 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 1.000 | 0.500 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `2.0`; mean tool calls: `4.0`; mean evidence chunks: `18.0`; mean planner tokens: `28161.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

See `results.json` for per-question answers, evidence, citations and scores.
