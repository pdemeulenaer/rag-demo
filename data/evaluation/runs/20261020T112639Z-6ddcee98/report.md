# Evaluation run 20261020T112639Z-6ddcee98

Dataset: `3dfe7bf8859748c92238b896dc437487cf5fdef1cd91de3a3f3ca131e1bf8f15`

Split: `development`; evaluation set: `f885b018479f30c00b0ae0f6c05c111557db9313b77d3b9edb83a9e316854fea`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 8 | 0 | 0 | 20.382 | 0.500 | 0.429 | 7 / 1 | 0.938 | 8 / 0 | 0.812 |
| kg | 8 | 7 | 0 | 4.917 | 1.000 | 1.000 | 1 / 7 | 1.000 | 1 / 7 | 1.000 |

## KG coverage

Pinned publication(s): publication:ef340620c8c35358052b02616a177172a1bdc4710641fe603f2fc127b447ba70.
Graph-supported runs: 1; Hybrid-only runs: 0.
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

- hybrid: 1 run(s) flagged during judging; question IDs still needing review: kg0007.
- kg: 0 run(s) flagged during judging; question IDs still needing review: none.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 12.000 | 0.927 | — | 17.708 | 6.218 | 2.163 | 20.382 |
| kg | 4.102 | 0.424 | — | 28.721 | 4.627 | 1.887 | 4.917 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 4 | 0 | 0.250 | 0.000 | 3 / 1 | 1.000 | 0.625 |
| single_fact | 2 | 0 | 0.500 | 0.500 | 2 / 0 | 0.750 | 1.000 |
| single_synthesis | 2 | 0 | 1.000 | 1.000 | 2 / 0 | 1.000 | 1.000 |

## kg by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 4 | 4 | — | — | — | — | — |
| single_fact | 2 | 2 | — | — | — | — | — |
| single_synthesis | 2 | 1 | 1.000 | 1.000 | 1 / 1 | 1.000 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
