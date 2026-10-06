# Evaluation run 20261006T110053Z-19e40923

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `33652665b3231e705348100ca5c1e727886a9d3c97daff7204c8cb560561e14a`

| Mode | Questions | Errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 1 | 0 | 118.453 | 0.750 | — | 0 / 1 | 1.000 | 1.000 |

## Judge consistency

Unresolved reference correctness is null/unscored, not zero or a promoted score.
Means use scored samples only; compare scored/unscored counts before comparing modes.
Unresolved contradictions/source ambiguities need manual review, not a conclusion of poor RAG quality.
A clean check means no detected conflict, not proof of semantic correctness.

- agentic: 0 run(s) flagged during judging; question IDs still needing review: q0046.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agentic | 87.896 | 11.761 | — | 76.126 | 27.182 | 3.374 | 118.453 |

### Agentic synthesis breakdown (seconds)

These sub-stages are already included in Generation above. Review combines
both attempts. Means cover measured runs only; repair means exclude runs
without repair (see sample_counts in summary.json).

| Mode | Draft | Review(s) | Repair (when run) |
| --- | ---: | ---: | ---: |
| agentic | 14.057 | 53.488 | 8.095 |

## agentic by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_multihop | 1 | 0 | 0.750 | — | 0 / 1 | 1.000 | 1.000 |

## Agentic execution

Mean rounds: `2.0`; mean tool calls: `5.0`; mean evidence chunks: `29.0`; mean planner tokens: `14287.0`. Named-paper full coverage: `1.0` across `1` detected runs.

| Stop reason | Runs |
| --- | ---: |
| token_budget | 1 |

Synthesis policy counts: `evidence_fallback`=1.
Planner preflight stopped 1 run(s); mean spent-plus-estimated-next-call tokens: `29068.0` (conservative estimate, not billed usage).
Planner context was compacted in 1 run(s), preserving original evidence and token limits.

See `results.json` for per-question answers, evidence, citations and scores.
