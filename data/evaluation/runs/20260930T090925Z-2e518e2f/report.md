# Evaluation run 20260930T090925Z-2e518e2f

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `3ff7dbe386b47d405022ebf7998c111c73a082b2bc6829e48f82c91aaa12f2d3`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 33 | 0 | 12.584 | 0.495 | 0.682 | 1.000 | 0.864 |
| hybrid | 33 | 0 | 15.742 | 0.558 | 0.773 | 0.955 | 0.909 |
| hybrid_rerank | 33 | 0 | 20.601 | 0.487 | 0.803 | 0.939 | 0.939 |
| agentic | 33 | 0 | 55.362 | 0.730 | 0.864 | 1.000 | 0.955 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.167 | 0.200 | 1.000 | 0.600 |
| cross_multihop | 5 | 0 | 0.317 | 0.200 | 1.000 | 0.600 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.731 | 0.923 | 1.000 | 1.000 |
| single_synthesis | 9 | 0 | 0.491 | 0.889 | 1.000 | 0.944 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.317 | 0.700 | 1.000 | 0.900 |
| cross_multihop | 5 | 0 | 0.317 | 0.200 | 0.700 | 0.600 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.756 | 0.962 | 1.000 | 0.962 |
| single_synthesis | 9 | 0 | 0.602 | 0.889 | 1.000 | 1.000 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.100 | 0.600 | 1.000 | 0.800 |
| cross_multihop | 5 | 0 | 0.267 | 0.400 | 0.700 | 0.800 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.679 | 0.962 | 0.962 | 1.000 |
| single_synthesis | 9 | 0 | 0.602 | 0.889 | 1.000 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.417 | 0.900 | 1.000 | 1.000 |
| cross_multihop | 5 | 0 | 0.483 | 0.900 | 1.000 | 0.900 |
| metadata_discovery | 1 | 0 | 0.750 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.897 | 0.846 | 1.000 | 0.962 |
| single_synthesis | 9 | 0 | 0.796 | 0.833 | 1.000 | 0.944 |

## Agentic execution

Mean rounds: `1.758`; mean tool calls: `3.121`; mean evidence chunks: `14.636`; mean planner tokens: `10505.061`. Named-paper full coverage: `1.0` across `29` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 13 |
| token_budget | 20 |

Synthesis policy counts: `evidence_fallback`=20, `model_finish`=13.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `3.091`; mean selected papers: `1.273`; mean paper-diversity retention: `0.5823`. Required-paper recall before/after reranking: `1.0` / `0.9848`.

See `results.json` for per-question answers, evidence, citations and scores.
