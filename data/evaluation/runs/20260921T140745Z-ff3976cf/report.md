# Evaluation run 20260921T140745Z-ff3976cf

Dataset: `c0cd09df44294628e866781056b8606a97e8db1c80b612bfdf6d512a366a87a4`

Split: `development`; evaluation set: `d48975c609b9be178052b2036bdf4a119a1eaf2e78bff5c0a1cf5083a36694fc`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 13.538 | 1.000 | 1.000 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_fact | 1 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `1.0`; mean tool calls: `1.0`; mean evidence chunks: `8.0`; mean planner tokens: `5926.0`.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

See `results.json` for per-question answers, evidence, citations and scores.
