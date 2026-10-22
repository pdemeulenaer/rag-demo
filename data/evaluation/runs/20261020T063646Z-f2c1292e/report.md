# Evaluation run 20261020T063646Z-f2c1292e

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `b0b9c925e7dff94c42e34de32e0f14ce5c47265bad0c7f768b0c1c4190715aae`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| kg | 1 | 0 | 0 | 41.482 | 0.000 | 0.500 | 1 / 0 | 1.000 | 1 / 0 | 1.000 |

## KG coverage

Pinned publication(s): publication:ef340620c8c35358052b02616a177172a1bdc4710641fe603f2fc127b447ba70.
Graph-supported runs: 0; Hybrid-only runs: 1.
The reviewed pilot graph covers only part of the corpus; do not attribute Hybrid-only answers to graph retrieval.

## Judge failures and grounding annotations

Judge errors do not discard completed RAG answers, evidence or retrieval metrics.
Invalid grounding annotations share the existing single retry; unresolved annotations
leave groundedness null/unscored, not a fabricated answer penalty.

- kg: 0 judge error(s); grounding question IDs needing review: none.

## Judge consistency

Unresolved reference correctness is null/unscored, not zero or a promoted score.
Means use scored samples only; compare scored/unscored counts before comparing modes.
Unresolved contradictions/source ambiguities need manual review, not a conclusion of poor RAG quality.
A clean check means no detected conflict, not proof of semantic correctness.

- kg: 0 run(s) flagged during judging; question IDs still needing review: none.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| kg | 32.134 | 2.619 | — | 29.509 | 6.344 | 3.000 | 41.482 |

## kg by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single_fact | 1 | 0 | 0.000 | 0.500 | 1 / 0 | 1.000 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
