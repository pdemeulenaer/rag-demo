# Evaluation run 20260916T102747Z-64233938

Dataset: `41c9b16cb96c2dce2d4b2d1ea640d85ca912d442e212ceef92c89327b5bfac10`

Split: `development`; evaluation set: `6896fc81ed345b1d1b88b5dbde18fcfa63085090cb05925bc20fd3c04c1317cb`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vanilla | 34 | 1 | 7.111 | 0.477 | 0.818 | 0.818 | 0.955 |
| hybrid | 34 | 1 | 6.69 | 0.482 | 0.833 | 0.864 | 0.970 |

## vanilla by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 1 | 0.083 | 0.750 | 0.750 | 0.750 |
| cross_multihop | 5 | 0 | 0.367 | 0.700 | 0.700 | 1.000 |
| metadata_discovery | 1 | 0 | 0.000 | 1.000 | 0.500 | 1.000 |
| single_fact | 16 | 0 | 0.625 | 0.844 | 0.875 | 1.000 |
| single_synthesis | 7 | 0 | 0.512 | 0.857 | 0.857 | 0.929 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 1 | 0.083 | 0.750 | 0.750 | 0.750 |
| cross_multihop | 5 | 0 | 0.367 | 0.700 | 0.700 | 1.000 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1.000 | 1.000 |
| single_fact | 16 | 0 | 0.646 | 0.938 | 0.969 | 1.000 |
| single_synthesis | 7 | 0 | 0.488 | 0.786 | 0.786 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
