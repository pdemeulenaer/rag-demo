# Evaluation run 20260925T112021Z-28a2da9d

Dataset: `9a5fceeaa18570bd7763a34702478ffe7cd235181a4445af9da19cfc6c161327`

Split: `development`; evaluation set: `b24a3d47748787eecd217c69743857f4936bc60bae994b1aebaa67769d520abe`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 20.411 | 1.000 | 1.000 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_fact | 1 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `2.0`; mean tool calls: `2.0`; mean evidence chunks: `7.0`; mean planner tokens: `12540.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

See `results.json` for per-question answers, evidence, citations and scores.
