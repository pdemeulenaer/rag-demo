# Evaluation run 20260924T052416Z-beb849a9

Dataset: `9a5fceeaa18570bd7763a34702478ffe7cd235181a4445af9da19cfc6c161327`

Split: `development`; evaluation set: `3ff7dbe386b47d405022ebf7998c111c73a082b2bc6829e48f82c91aaa12f2d3`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 33 | 0 | 6.199 | 0.495 | 0.667 | 0.939 | 0.864 |
| hybrid | 33 | 0 | 6.299 | 0.558 | 0.712 | 0.894 | 0.894 |
| hybrid_rerank | 33 | 0 | 7.611 | 0.477 | 0.773 | 0.849 | 0.909 |
| agentic | 33 | 0 | 19.644 | 0.692 | 0.636 | 0.894 | 0.909 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.167 | 0.000 | 1.000 | 0.800 |
| cross_multihop | 5 | 0 | 0.317 | 0.300 | 0.800 | 0.700 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1.000 | 0.500 |
| single_fact | 13 | 0 | 0.731 | 0.962 | 1.000 | 0.962 |
| single_synthesis | 9 | 0 | 0.491 | 0.833 | 0.889 | 0.889 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.317 | 0.400 | 0.900 | 0.900 |
| cross_multihop | 5 | 0 | 0.317 | 0.300 | 0.700 | 0.600 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.756 | 0.923 | 0.923 | 1.000 |
| single_synthesis | 9 | 0 | 0.602 | 0.778 | 0.944 | 0.889 |

## hybrid_rerank by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.100 | 0.600 | 0.800 | 0.700 |
| cross_multihop | 5 | 0 | 0.267 | 0.600 | 0.500 | 0.800 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.679 | 0.885 | 0.962 | 0.962 |
| single_synthesis | 9 | 0 | 0.565 | 0.833 | 0.889 | 1.000 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.467 | 0.300 | 0.800 | 0.800 |
| cross_multihop | 5 | 0 | 0.533 | 0.600 | 0.900 | 0.800 |
| metadata_discovery | 1 | 0 | 0.500 | 0.000 | 0.500 | 1.000 |
| single_fact | 13 | 0 | 0.808 | 0.808 | 0.923 | 0.923 |
| single_synthesis | 9 | 0 | 0.759 | 0.667 | 0.944 | 1.000 |

## Agentic execution

Mean rounds: `1.636`; mean tool calls: `3.061`; mean evidence chunks: `12.818`; mean planner tokens: `13357.788`. Named-paper full coverage: `1.0` across `29` detected runs.

| Stop reason | Runs |
| --- | ---: |
| sufficient | 25 |
| token_budget | 8 |

Synthesis policy counts: `evidence_fallback`=8, `model_finish`=25.

## Hybrid + Rerank candidate diagnostics

Mean candidates: `20.0`; mean candidate papers: `3.152`; mean selected papers: `1.273`; mean paper-diversity retention: `0.5748`. Required-paper recall before/after reranking: `1.0` / `0.9848`.

See `results.json` for per-question answers, evidence, citations and scores.
