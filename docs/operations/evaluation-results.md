# Evaluation results

This page records named comparison baselines. Local run artifacts remain the authoritative
per-question record, and Langfuse holds the corresponding traces and Dataset Experiments.

## Baseline 1 — Vanilla versus legacy Hybrid

Run `20260915T092511Z-afa2f2d4`, completed on 15 September 2026 with no errors.

| Setting | Value |
| --- | --- |
| Reviewed questions | 38: 29 single-paper, 9 cross-paper |
| Frozen corpus | 48 paper builds; fingerprint `c82f55936519d46de11f` |
| Retrieval depth | `top_k=5` |
| Answer model | `gpt-4.1-nano` |
| Judge | `gpt-5-mini`, minimal reasoning |
| Modes | Vanilla dense retrieval; legacy full-text-constrained RRF plus Cohere reranking |

| Metric | Vanilla | Hybrid | Hybrid change |
| --- | ---: | ---: | ---: |
| Retrieval hit | 0.8158 | **0.8947** | +0.0789 |
| Retrieval recall | 0.5478 | **0.5991** | +0.0513 |
| Answer correctness | 0.8684 | **0.9211** | +0.0527 |
| Groundedness | 0.8553 | **0.9342** | +0.0789 |
| Answer relevance | 0.9342 | **0.9737** | +0.0395 |
| Gold-citation recall | **0.4320** | 0.4307 | -0.0013 |
| Citation from retrieval | 1.0000 | 1.0000 | 0.0000 |
| Mean latency | 8.743 s | 8.349 s | -0.394 s |

The legacy Hybrid pipeline is the stronger baseline for this run: it raises retrieval coverage and the three
judge-scored answer measures. The nearly unchanged, relatively low gold-citation recall
shows that both modes still often miss or do not select the exact reviewed evidence. A
good next mode should therefore be able to decompose a question, search again with a more
specific query, retrieve from named papers/sections, and stop only when its evidence is
sufficient. The small latency difference is not evidence that Hybrid is faster; one run
without repeated timing trials cannot establish that.

!!! warning "Historical implementation"
    This run predates the named BM25 sparse index and the separation of `hybrid` from
    `hybrid_rerank`. Do not attribute these scores to either current mode. Re-index into the
    v2 collection, create a new frozen dataset, and benchmark all four current modes.

### Interpretation limits

- This is a directional development baseline, not a statistically conclusive result.
- The questions and reference answers began as synthetic drafts and were manually reviewed.
- The reviewed set contains no accepted unanswerable cases, so abstention is not tested.
- There is no held-out split, repeated run, confidence interval or human answer grading yet.
- `citation_from_retrieval=1` means cited IDs came from retrieved chunks; it does not prove
  that every citation supports the answer.
- `gold_citation_recall` is deliberately strict: an alternative valid passage can support an
  answer while scoring as a miss against the reviewed point IDs.

The local artifacts are under
`data/evaluation/runs/20260915T092511Z-afa2f2d4/`. The dataset hash is
`e7031deaee8718bac7e8ece006fc1df8906395b1943c24b876ef1a8729c5e539`.

## Baseline 2 — four current modes before coverage enforcement

Run `20260922T052035Z-38e2702f`, completed on 22 September 2026 with no runtime
errors. It used 33 development questions from dense+sparse v4, `top_k=5`, answer model
`gpt-4.1-nano`, and `gpt-5-mini` judging. Agentic used four rounds, 16 tool calls,
40 evidence chunks, 150 seconds and a 6,000 cumulative planner-token threshold.

| Metric | Vanilla | Hybrid | Hybrid + Rerank | Agentic |
| --- | ---: | ---: | ---: | ---: |
| Retrieval recall | 0.4949 | **0.5581** | 0.4773 | 0.5253 |
| Gold-citation recall | 0.2778 | **0.4015** | 0.3258 | 0.3157 |
| Answer correctness | 0.7879 | 0.8182 | 0.8030 | **0.8485** |
| Groundedness | 0.8030 | **0.8485** | 0.8030 | **0.8485** |
| Mean latency | 4.934 s | 4.972 s | **4.828 s** | 10.844 s |

Agentic completed normally in 23 cases and used evidence fallback after the token threshold
in 10. Model-finished answers averaged 0.913 correctness and 0.935 groundedness; fallback
answers averaged only 0.700 and 0.650. Four of five cross-comparison and four of five
cross-multihop items hit the token threshold. Item inspection found that only four of ten
cross-paper questions retrieved both intended papers, so higher global limits alone were not
the appropriate next correction.

Hybrid + Rerank underperformed plain Hybrid on deterministic retrieval measures, especially
cross-paper profiles. The historical run did not persist Cohere's full candidate order, so it
cannot distinguish candidate-generation failure from a global top-five reranker collapsing
paper diversity. Subsequent code records all 20 ranked candidates and candidate/selected paper
counts without yet changing selection.

!!! warning "Historical judge leakage"
    This run used one combined judge request containing both gold/reference evidence and
    retrieved evidence. At least one item received full groundedness despite missing one named
    paper from retrieval, showing that the model could confuse gold evidence with retrieved
    support. Treat its groundedness values as optimistic. Later runs isolate the grounding
    judge and provide it no reference answer or gold evidence.

The local artifacts are under
`data/evaluation/runs/20260922T052035Z-38e2702f/`. The dataset hash is
`c0cd09df44294628e866781056b8606a97e8db1c80b612bfdf6d512a366a87a4`.
