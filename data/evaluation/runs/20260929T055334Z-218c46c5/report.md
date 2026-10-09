# Evaluation run 20260929T055334Z-218c46c5

Dataset: `65e2a571824e40e5c843cadf410b772ac7ff679d6fe56804f92f3534f1e28a30`

Split: `development`; evaluation set: `d45aa3a332a139714a7a432e9fe8269816957f870760f65e952bc349e8528dfa`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 44.399 | 0.667 | 0.500 | 1.000 | 0.500 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.667 | 0.500 | 1.000 | 0.500 |

## Agentic execution

Mean rounds: `1.0`; mean tool calls: `3.0`; mean evidence chunks: `18.0`; mean planner tokens: `13749.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 1 |

Synthesis policy counts: `model_finish`=1.

See `results.json` for per-question answers, evidence, citations and scores.
