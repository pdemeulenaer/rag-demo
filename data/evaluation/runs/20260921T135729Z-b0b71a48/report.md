# Evaluation run 20260921T135729Z-b0b71a48

Dataset: `c0cd09df44294628e866781056b8606a97e8db1c80b612bfdf6d512a366a87a4`

Split: `development`; evaluation set: `0f0800f94e7d94f09ebfa5d06e5343c7803171a236f28f6e745baf51102e1db1`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 18.889 | 1.000 | 1.000 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_fact | 1 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `2.0`; mean tool calls: `2.0`; mean evidence chunks: `13.0`; mean planner tokens: `14179.0`.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

See `results.json` for per-question answers, evidence, citations and scores.
