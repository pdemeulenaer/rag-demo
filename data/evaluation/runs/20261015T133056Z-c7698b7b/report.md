# Evaluation run 20261015T133056Z-c7698b7b

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `2ec1565a3058fe5883cf6540a85c64ec0d2c75190b01311e4407d493e6f8cdd3`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 2 | 0 | 0 | 26.122 | 0.500 | 0.750 | 2 / 0 | 1.000 | 2 / 0 | 1.000 |
| kg | 2 | 0 | 0 | 23.606 | 0.500 | 0.500 | 2 / 0 | 1.000 | 2 / 0 | 1.000 |

## KG coverage

Pinned publication(s): publication:e1a26713b02bf59482d9cebbd3cd514eb236579769e9751f3bc545e7dfad896a.
Graph-supported runs: 0; Hybrid-only runs: 2.
The reviewed pilot graph covers only part of the corpus; do not attribute Hybrid-only answers to graph retrieval.

## Judge failures and grounding annotations

Judge errors do not discard completed RAG answers, evidence or retrieval metrics.
Invalid grounding annotations share the existing single retry; unresolved annotations
leave groundedness null/unscored, not a fabricated answer penalty.

- hybrid: 0 judge error(s); grounding question IDs needing review: none.
- kg: 0 judge error(s); grounding question IDs needing review: none.

## Judge consistency

Unresolved reference correctness is null/unscored, not zero or a promoted score.
Means use scored samples only; compare scored/unscored counts before comparing modes.
Unresolved contradictions/source ambiguities need manual review, not a conclusion of poor RAG quality.
A clean check means no detected conflict, not proof of semantic correctness.

- hybrid: 0 run(s) flagged during judging; question IDs still needing review: none.
- kg: 0 run(s) flagged during judging; question IDs still needing review: none.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 19.418 | 1.377 | — | 18.035 | 4.534 | 2.167 | 26.122 |
| kg | 16.095 | 0.589 | — | 15.498 | 5.398 | 2.112 | 23.606 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single_fact | 2 | 0 | 0.500 | 0.750 | 2 / 0 | 1.000 | 1.000 |

## kg by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single_fact | 2 | 0 | 0.500 | 0.500 | 2 / 0 | 1.000 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
