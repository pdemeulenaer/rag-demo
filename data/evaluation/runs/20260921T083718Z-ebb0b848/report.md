# Evaluation run 20260921T083718Z-ebb0b848

Dataset: `c0cd09df44294628e866781056b8606a97e8db1c80b612bfdf6d512a366a87a4`

Split: `development`; evaluation set: `3ff7dbe386b47d405022ebf7998c111c73a082b2bc6829e48f82c91aaa12f2d3`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 33 | 0 | 6.762 | 0.495 | 0.818 | 0.818 | 0.955 |
| hybrid | 33 | 0 | 5.0 | 0.558 | 0.833 | 0.864 | 0.939 |
| hybrid_rerank | 33 | 0 | 5.089 | 0.477 | 0.849 | 0.833 | 0.970 |
| agentic | 33 | 1 | 9.874 | 0.529 | 0.781 | 0.766 | 0.875 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.167 | 0.700 | 0.700 | 0.800 |
| cross_multihop | 5 | 0 | 0.317 | 0.700 | 0.700 | 1.000 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.731 | 0.885 | 0.885 | 1.000 |
| single_synthesis | 9 | 0 | 0.491 | 0.833 | 0.833 | 0.944 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.317 | 0.800 | 0.800 | 0.800 |
| cross_multihop | 5 | 0 | 0.317 | 0.600 | 0.700 | 1.000 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.756 | 0.962 | 0.962 | 1.000 |
| single_synthesis | 9 | 0 | 0.602 | 0.778 | 0.833 | 0.889 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.100 | 0.600 | 0.600 | 0.900 |
| cross_multihop | 5 | 0 | 0.267 | 0.700 | 0.700 | 0.900 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.679 | 0.962 | 0.962 | 1.000 |
| single_synthesis | 9 | 0 | 0.565 | 0.889 | 0.833 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.450 | 0.700 | 0.700 | 0.800 |
| cross_multihop | 5 | 0 | 0.300 | 0.500 | 0.500 | 0.700 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 1 | 0.806 | 0.958 | 0.958 | 0.958 |
| single_synthesis | 9 | 0 | 0.389 | 0.722 | 0.667 | 0.889 |

See `results.json` for per-question answers, evidence, citations and scores.
