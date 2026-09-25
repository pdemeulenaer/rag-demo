# Evaluation run 20260925T113307Z-2d318ba9

Dataset: `9a5fceeaa18570bd7763a34702478ffe7cd235181a4445af9da19cfc6c161327`

Split: `development`; evaluation set: `3ff7dbe386b47d405022ebf7998c111c73a082b2bc6829e48f82c91aaa12f2d3`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 33 | 0 | 29.62 | 0.619 | 0.833 | 0.879 | 0.924 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.350 | 0.700 | 0.800 | 0.900 |
| cross_multihop | 5 | 0 | 0.417 | 0.600 | 0.700 | 0.700 |
| metadata_discovery | 1 | 0 | 0.250 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.769 | 0.962 | 0.962 | 1.000 |
| single_synthesis | 9 | 0 | 0.704 | 0.833 | 0.889 | 0.944 |

## Agentic execution

Mean rounds: `1.818`; mean tool calls: `4.576`; mean evidence chunks: `12.273`; mean planner tokens: `20460.606`. Named-paper full coverage: `1.0` across `29` detected runs.

| Stop reason | Runs |
| --- | ---: |
| insufficient_evidence | 5 |
| planner_failure | 1 |
| sufficient | 22 |
| token_budget | 5 |

Synthesis policy counts: `evidence_fallback`=11, `model_finish`=22.

See `results.json` for per-question answers, evidence, citations and scores.
