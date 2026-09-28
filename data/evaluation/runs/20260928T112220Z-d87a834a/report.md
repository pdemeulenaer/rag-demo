# Evaluation run 20260928T112220Z-d87a834a

Dataset: `9a5fceeaa18570bd7763a34702478ffe7cd235181a4445af9da19cfc6c161327`

Split: `development`; evaluation set: `c3154dae7fe50d34b46058cefb717338dc209ae9dc2446d123358e14306e854a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 57.133 | 1.000 | 0.000 | 1.000 | 0.500 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_synthesis | 1 | 0 | 1.000 | 0.000 | 1.000 | 0.500 |

## Agentic execution

Mean rounds: `1.0`; mean tool calls: `3.0`; mean evidence chunks: `14.0`; mean planner tokens: `13546.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

See `results.json` for per-question answers, evidence, citations and scores.
