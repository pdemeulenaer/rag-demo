# Evaluation run 20260923T124730Z-687f69ac

Dataset: `c44a47c2c0e5609eebead972c8ef04f028a51ae9abc5c58a0ef1581b340b3930`

Split: `development`; evaluation set: `3ff7dbe386b47d405022ebf7998c111c73a082b2bc6829e48f82c91aaa12f2d3`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 33 | 0 | 8.078 | 0.495 | 0.591 | 0.909 | 0.833 |
| hybrid | 33 | 0 | 8.767 | 0.558 | 0.651 | 0.924 | 0.864 |
| hybrid_rerank | 33 | 0 | 10.535 | 0.477 | 0.773 | 0.849 | 0.849 |
| agentic | 33 | 0 | 26.137 | 0.682 | 0.606 | 0.939 | 0.833 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.167 | 0.000 | 0.900 | 0.600 |
| cross_multihop | 5 | 0 | 0.317 | 0.200 | 0.800 | 0.700 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.731 | 0.923 | 0.962 | 0.962 |
| single_synthesis | 9 | 0 | 0.491 | 0.611 | 0.889 | 0.833 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.317 | 0.400 | 1.000 | 0.700 |
| cross_multihop | 5 | 0 | 0.317 | 0.100 | 0.800 | 0.500 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1.000 | 0.500 |
| single_fact | 13 | 0 | 0.756 | 0.923 | 0.923 | 1.000 |
| single_synthesis | 9 | 0 | 0.602 | 0.722 | 0.944 | 1.000 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.100 | 0.600 | 0.700 | 0.600 |
| cross_multihop | 5 | 0 | 0.267 | 0.600 | 0.600 | 0.800 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.679 | 0.885 | 0.923 | 0.923 |
| single_synthesis | 9 | 0 | 0.565 | 0.833 | 0.944 | 0.889 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.467 | 0.300 | 0.800 | 0.900 |
| cross_multihop | 5 | 0 | 0.633 | 0.600 | 1.000 | 0.900 |
| metadata_discovery | 1 | 0 | 0.250 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.782 | 0.577 | 0.962 | 0.769 |
| single_synthesis | 9 | 0 | 0.732 | 0.778 | 0.944 | 0.833 |

## Agentic execution

Mean rounds: `1.515`; mean tool calls: `3.061`; mean evidence chunks: `12.636`; mean planner tokens: `12489.697`. Named-paper full coverage: `1.0` across `29` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 30 |
| token_budget | 2 |
| tool_failure | 1 |

Synthesis policy counts: `evidence_fallback`=2, `hard_stop`=1, `model_finish`=30.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `3.212`; mean selected papers: `1.273`; mean paper-diversity retention: `0.5718`. Required-paper recall before/after reranking: `1.0` / `0.9848`.

See `results.json` for per-question answers, evidence, citations and scores.
