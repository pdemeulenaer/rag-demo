# Evaluation run 20261020T055958Z-9846b750

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `cbf4821add6956dc5bff65022602f4070280f8600cb09ce3e5f8064bba981a27`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 5 | 0 | 0 | 22.443 | 0.800 | 0.900 | 5 / 0 | 0.900 | 5 / 0 | 1.000 |
| kg | 5 | 1 | 0 | 98.301 | 1.000 | 1.000 | 4 / 1 | 1.000 | 4 / 1 | 1.000 |

## KG coverage

Pinned publication(s): publication:ef340620c8c35358052b02616a177172a1bdc4710641fe603f2fc127b447ba70.
Graph-supported runs: 1; Hybrid-only runs: 4.
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
| hybrid | 14.960 | 0.769 | — | 14.184 | 4.606 | 2.876 | 22.443 |
| kg | 92.838 | 0.895 | — | 91.937 | 4.386 | 2.441 | 98.301 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single_fact | 5 | 0 | 0.800 | 0.900 | 5 / 0 | 0.900 | 1.000 |

## kg by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single_fact | 5 | 1 | 1.000 | 1.000 | 4 / 1 | 1.000 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
