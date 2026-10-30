# Evaluation run 20261023T120303Z-ecec5bb4

Dataset: `b424ac8455d9622452adb6e005a06cc61ef7c716270ddbfdfdbf6d4133d3ca2d`

Split: `development`; evaluation set: `3ff7dbe386b47d405022ebf7998c111c73a082b2bc6829e48f82c91aaa12f2d3`

| Mode | Questions | RAG errors | Judge errors | Mean latency (s) | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Groundedness scored / unscored | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 33 | 0 | 0 | 27.166 | 0.558 | 0.828 | 32 / 1 | 0.970 | 33 / 0 | 0.985 |
| kg | 33 | 0 | 0 | 24.759 | 0.558 | 0.855 | 31 / 2 | 0.955 | 33 / 0 | 0.985 |

## KG coverage

Pinned publication(s): publication:ef340620c8c35358052b02616a177172a1bdc4710641fe603f2fc127b447ba70.
Graph-used runs (policy-defined): 2; Hybrid-only runs: 31.
The reviewed pilot graph covers only part of the corpus; do not attribute Hybrid-only answers to graph retrieval.

Bounded selection runs: 33; actual graph-expansion runs: 2; mean protected Hybrid chunks: 3.0.
Displaced Hybrid chunks: 3; rejected promotion candidates: {"no_named_fact_or_entity_match": 1}.
A graph-supported chunk already retrieved by Hybrid is not an actual graph expansion.
Expansion qualification bases: {"named_paper_fact_overlap": 2, "specific_entity_path": 1}.

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

- hybrid: 4 run(s) flagged during judging; question IDs still needing review: q0021.
- kg: 2 run(s) flagged during judging; question IDs still needing review: q0021, q0022.

## Mean stage timings (seconds)

The total includes judging and local evaluation work. Retrieval includes reranking;
rerank and judge sub-stages overlap their parent timings and must not be added again.
A dash means the stage was not run or was not measured.

| Mode | RAG pipeline | Retrieval | Rerank | Generation | Reference judge | Grounding judge | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | 19.041 | 0.598 | — | 18.431 | 5.523 | 2.600 | 27.166 |
| kg | 17.384 | 0.642 | — | 16.735 | 4.797 | 2.575 | 24.759 |

### Retrieval breakdown (seconds)

Already included in Retrieval above. Embedding includes configured SDK retries;
Qdrant measures query_points calls only, excluding embedding and BM25 encoding.
Repeated/parallel calls are summed, so these work durations can exceed wall time.
Failed calls retain elapsed time; absent stages are not fabricated as zero.

| Mode | Embedding | Qdrant | Graph |
| --- | ---: | ---: | ---: |
| hybrid | 0.326 | 0.260 | — |
| kg | 0.255 | 0.264 | 0.076 |

## hybrid by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.317 | 0.800 | 5 / 0 | 1.000 | 1.000 |
| cross_multihop | 5 | 0 | 0.317 | 0.500 | 5 / 0 | 0.800 | 0.900 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1 / 0 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.756 | 0.923 | 13 / 0 | 1.000 | 1.000 |
| single_synthesis | 9 | 0 | 0.602 | 0.938 | 8 / 1 | 1.000 | 1.000 |

## kg by question profile

| Profile | Questions | Errors | Retrieval recall | Correctness | Correctness scored / unscored | Groundedness | Relevance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_comparison | 5 | 0 | 0.317 | 0.800 | 5 / 0 | 1.000 | 1.000 |
| cross_multihop | 5 | 0 | 0.317 | 0.600 | 5 / 0 | 0.700 | 0.900 |
| metadata_discovery | 1 | 0 | 0.000 | 0.500 | 1 / 0 | 1.000 | 1.000 |
| single_fact | 13 | 0 | 0.756 | 0.962 | 13 / 0 | 1.000 | 1.000 |
| single_synthesis | 9 | 0 | 0.602 | 0.929 | 7 / 2 | 1.000 | 1.000 |

See `results.json` for per-question answers, evidence, citations and scores.
