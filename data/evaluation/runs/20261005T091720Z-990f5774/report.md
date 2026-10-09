# Evaluation run 20261005T091720Z-990f5774

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `33652665b3231e705348100ca5c1e727886a9d3c97daff7204c8cb560561e14a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 55.954 | 0.250 | 0.000 | 0.500 | 0.500 |

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 50.354 | 13.063 | — | 37.284 | 3.846 | 1.752 | 55.954 |

### Agentic synthesis breakdown (seconds)

These sub-stages are already included in Generation above. Review combines
both attempts. Means cover measured runs only; repair means exclude runs
without repair (see sample_counts in summary.json).

| Mode | Draft | Review(s) | Repair (when run) |
| --- | ---: | ---: | ---: |
| agentic | 16.531 | 1.200 | 19.167 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.250 | 0.000 | 0.500 | 0.500 |

## Agentic execution

Mean rounds: `2.0`; mean tool calls: `4.0`; mean evidence chunks: `23.0`; mean planner tokens: `11613.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| token_budget | 1 |

Synthesis policy counts: `evidence_fallback`=1.
Planner preflight stopped 1 run(s); mean spent-plus-estimated-next-call tokens: `24349.0` (conservative estimate, not billed usage).

See `results.json` for per-question answers, evidence, citations and scores.
