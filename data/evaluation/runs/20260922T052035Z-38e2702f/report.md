# Evaluation run 20260922T052035Z-38e2702f

Dataset: `c0cd09df44294628e866781056b8606a97e8db1c80b612bfdf6d512a366a87a4`

Split: `development`; evaluation set: `3ff7dbe386b47d405022ebf7998c111c73a082b2bc6829e48f82c91aaa12f2d3`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 33 | 0 | 4.934 | 0.495 | 0.788 | 0.803 | 0.939 |
| hybrid | 33 | 0 | 4.972 | 0.558 | 0.818 | 0.849 | 0.985 |
| hybrid_rerank | 33 | 0 | 4.828 | 0.477 | 0.803 | 0.803 | 0.970 |
| agentic | 33 | 0 | 10.844 | 0.525 | 0.849 | 0.849 | 0.970 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.167 | 0.700 | 0.700 | 0.700 |
| cross_multihop | 5 | 0 | 0.317 | 0.700 | 0.700 | 1.000 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 0.500 | 1.000 |
| single_fact | 13 | 0 | 0.731 | 0.885 | 0.885 | 1.000 |
| single_synthesis | 9 | 0 | 0.491 | 0.778 | 0.833 | 0.944 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.317 | 0.700 | 0.800 | 0.900 |
| cross_multihop | 5 | 0 | 0.317 | 0.700 | 0.700 | 1.000 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.756 | 0.923 | 0.923 | 1.000 |
| single_synthesis | 9 | 0 | 0.602 | 0.833 | 0.833 | 1.000 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.100 | 0.600 | 0.600 | 0.800 |
| cross_multihop | 5 | 0 | 0.267 | 0.500 | 0.500 | 1.000 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.679 | 0.962 | 0.962 | 1.000 |
| single_synthesis | 9 | 0 | 0.565 | 0.833 | 0.833 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.233 | 0.600 | 0.600 | 0.800 |
| cross_multihop | 5 | 0 | 0.200 | 0.700 | 0.700 | 1.000 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 0.500 | 1.000 |
| single_fact | 13 | 0 | 0.782 | 0.923 | 0.962 | 1.000 |
| single_synthesis | 9 | 0 | 0.556 | 0.944 | 0.944 | 1.000 |

## Agentic execution

Mean rounds: `1.545`; mean tool calls: `1.545`; mean evidence chunks: `9.303`; mean planner tokens: `8257.818`.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 23 |
| token_budget | 10 |

Synthesis policy counts: `evidence_fallback`=10, `model_finish`=23.

See `results.json` for per-question answers, evidence, citations and scores.
