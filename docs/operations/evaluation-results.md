# Evaluation results

This page records named comparison baselines. Local run artifacts remain the authoritative
per-question record, and Langfuse holds the corresponding traces and Dataset Experiments.

!!! warning "Answer anchoring in newer evaluations"
    Manual inspection of q0046 in run `20261005T072551Z-f040caaa` found that the
    reference judge awarded full correctness while attributing reference-only sensitivity
    values to the generated answer. Treat that score as unreliable, not evidence of full
    coverage. New runs record `judge_policy: claim-anchored-v12`, use actual-answer claim IDs
    and numeric checks, and audit method/source-operation attribution. Historical artifacts
    remain unchanged; compare modes using
    fresh runs with the same judge policy. See [the evaluation guide](evaluation.md).

Inspection of q0046 in `20261005T100735Z-d2bf7141` found a different problem: the answer
contained the requested rate range and outer-radius values, but v2's deterministic guard
lowered the raw judge's correctness from `1.0` to `0.5` because of range/percentage parsing
and quote formatting. Runtime completeness also demanded an optional percentage format
and an unrequested quantitative derivation. The code now normalizes those numeric formats,
bounds quote-format repair, and guides completeness by the original question. This is a
diagnosis of that development item, not proof that its whole answer is correct or that the
new pipeline is faster. Historical scores remain unchanged; rerun under v3 before comparing.

Inspection of the subsequent q0046 run `20261005T122901Z-35da5381` found a real missing
detail: it listed the tested outer-radius settings but did not report their outcome effect.
Runtime review nevertheless marked the answer complete. The reference judge also returned
malformed numeric targets (`"[]"` and symbolic settings), so its correctness penalty was not
a reliable diagnosis of that gap. The run took 84.806 s, versus 120.412 s in the preceding
run, but that single timing is not a general latency result.

The next revision requires explicit reported-effect assessments linked to supported claims,
constrains judge numeric targets to decimal strings (`answer-anchored-v4`), and guides
bounded in-paper recovery toward outcome/parameter-change passages. It adds no normal-path
provider calls or budget increases. These are implemented safeguards, not evidence of live
quality improvements: rerun q0046, then the development split with all four modes, under the
same judge policy. Historical results and reviewed answers remain unchanged.

In q0046 run `20261006T052603Z-53f27afa`, the outer-radius effect was correctly included
and the enlarged judge budget succeeded on the first reference/grounding requests (1,511
reference output tokens). The reference judge's aggregate assessment said the answer matched,
but it labelled the quoted mass-dependent rates `partial` without naming a missing detail.
The safeguard therefore lowered raw correctness from 1.0 to 0.5. Manual comparison found
that quoted rate statement matched the retrieved source, making this an unexplained judge
disagreement rather than an established generation deficit. Historical scores stay unchanged.

Total latency was 173.188 s: a first draft timed out after 60.155 s, its replacement took
45.279 s, and verification took 24.168 s. Retrieval took 25.393 s; judging took 17.852 s.
This motivated v5's explicit per-check deficit explanations and an opt-in low-draft-reasoning
trial, not relaxed safeguards, higher timeouts or extra retries. The changes need fresh
live evaluation; offline tests alone cannot establish speed or quality improvements.

The low-draft-reasoning trial `20261006T095229Z-97635aa2` took 82.351 s, with generation
33.821 s and a 54.165 s RAG pipeline excluding evaluation judges. This is promising compared
with the previous timed-out draft, but one run is not a controlled estimate of the speedup.
Runtime marked the answer complete and groundedness was 1.0. Reference correctness remained
0.5; inspection found that the judge alleged a missing "20%" threshold while quoting that
threshold, and penalized an inner-radius value over damaged picture text. The cited retrieved
prose supports the radius, but the reviewed reference selection lacks that clear prose/caption.
Thus the reference judge cannot independently settle it from its limited material. The schema
warning recovered via the existing retry; there was no final benchmark error.

Version 6 exposes omission contradictions and unresolved reference ambiguity, with one shared
repair and persistent review flags rather than automatic score promotion. Retrieval, generation,
reasoning defaults, historical scores and reference evidence stay unchanged. Rerun under the
current judge policy before comparing modes; manually inspect flagged reference assessments.

Run `20261006T101036Z-ba887282` failed during reference judging because a check marked
`answered` also supplied a nonempty deficit; v6's cross-field Pydantic validator exhausted
the bounded retry and discarded the per-item answer/metrics. This is a judge consistency
failure, not evidence that retrieval failed or generation was incorrect. Total time was
163.784 s, including 99.455 s generation and 35.225 s reference judging; no grounding judge
ran, so this run has no usable correctness or grounding score.

Version 7 retains structurally valid contradictory assessments for one bounded repair. If
unresolved, reference correctness is null/unscored, the RAG result is preserved, and isolated
grounding still runs. Summaries/reports show scored/unscored counts; judge failures must not
be mistaken for zero correctness or inflated success. Historical runs are untouched. Offline
tests exercise the native SDK and item-persistence path; live improvement needs a fresh run.

In run `20261006T141305Z-458dc7d8`, claim-ID judging avoided copied-quote failures, but q0046
still scored correctness `0.5`. Inspection found a missing requested outer-radius effect,
abbreviated citation IDs misread as numbers during runtime review, and a method credited with
another pipeline step's operation. Total time was 93.864 s, including 14.124 s retrieval and
70.235 s generation. The general correction separates baseline/effect search targets, cleans
confirmed citation prefixes and records typed source-operation audits in the existing reviews
(judge policy v9). No expected q0046 values are injected, and no historical scores or datasets
are changed. A fresh run must establish whether these fixes improve correctness and latency.

Run `20261007T074109Z-c730e0fb` exposed a v9 regression: retrieval found the requested rate
and outer-radius effect (gold recall `0.75`), and the draft stated them, but the runtime
method audit incorrectly annotated ordinary facts with `method: "[]"` and removed them.
The repair's review then failed with `APIConnectionError` after 60.047 s, retaining just one
claim. Total latency was 223.807 s: retrieval 63.654 s, generation 136.512 s, judges 23.629 s.
The remaining claim also misattributed a companion-identification routine to a membership
algorithm. Conditional method auditing and literal claim/source bindings (runtime v2, judge
v10) address these failure classes without dropping semantic/numeric checks or increasing
budgets. Historical results remain unchanged; a new run must verify quality and latency.

The next q0046 run, `20261007T092753Z-8c886f5f`, never tested those answer fixes:
the initial `define_requirements` call had a schema `missing` error and stopped with zero
retrieval rounds, tools and evidence. Logs did not identify the omitted field, so its exact
identity is unknown. Retrieval/planning took 7.811 s and total evaluation took 15.125 s.
The graph now records safe field paths and permits one corrective native definition call
within unchanged token/time limits. This is planner recovery, not a reason to re-index or
raise budgets. Offline tests verify protocol, retry bounds and scope protection; a fresh
live run is still needed. Historical results are unchanged.

Run `20261007T111708Z-4d4d22ac` retrieved both named papers and received correctness,
relevance and groundedness of 1.0, but runtime coverage still labelled the answer partial.
The final answer stated the requested rate and outer-radius effect and then contradicted
itself with a broad missing-requirement warning. Inspection found a supplementary slope
claim rejected because `γ ∼−_ 1 _._ 75` was not recognized as -1.75, and coverage invalidating
an entire requirement when any related claim was rejected or absent. Raw coverage links
were not recorded then, so the exact offending link cannot be established retrospectively.

Runtime coverage v4 adds native essential-claim links and specific missing-detail records,
retains conservative checks on required facts, and omits rejected optional background
without a repair when every requested fact is verified. Approximation-bound sign cleanup
addresses the observed numeric format without changing stored chunks or guessing signs.
These fixes need fresh evaluation; full judge scores alone do not establish complete runtime
coverage. The application pipeline took 105.615 s, including 58.050 s across two verification
calls; judges added 35.661 s, including a bounded reference retry. Avoiding an unnecessary
repair/review pair may reduce latency, but no live speedup has yet been measured. Models,
budgets, reference datasets and historical scores remain unchanged.

Run `20261007T130312Z-12e8c645` failed during reference judging with a connection
interruption after the RAG pipeline had returned in 56.373 s. The old runner discarded the
completed answer, so its quality cannot be established from that saved result. A rerun
without code changes, `20261007T131308Z-c3829f66`, completed in 86.833 s (58.887 s pipeline,
27.938 s judges), consistent with a transient connection problem but not proof of its cause.

The successful rerun contains a genuine missing requested fact: it states the disruption
rate and outer-radius test settings but not the reported outer-radius outcome. Runtime v4
nevertheless marked it complete. The reference judge's raw 1.0 was reduced to 0.5 by missing
numeric answer targets. Separately, raw groundedness 1.0 was capped at 0.5 because a method
audit failed to quote the actual claim wording. That malformed annotation is not proof that
the claim itself was unsupported. Retrieval stopped at the planner-token reservation limit;
finding both papers did not establish complete factual coverage.

Runtime v5 requires explicit answer-bound parameter/outcome audits; judge v11 corrects
malformed grounding annotations once, leaving unresolved scores unscored rather than
fabricating penalties. Judge transport/schema failures now preserve completed RAG outputs
with separate `judge_error` diagnostics and failed-stage scores null. These changes need a
fresh development rerun: mock tests establish schema/protocol/failure behavior, not live
scientific correctness or a latency improvement. No historical artifacts or reviewed answers
are changed, and no re-index or new evaluation dataset is required.

Run `20261007T133250Z-f1925435` scored correctness, relevance and groundedness 1.0, with
no RAG/judge errors and both required papers retrieved/cited. Runtime still marked q0046
partial: its effect audit copied source wording rather than the actual answer wording,
although the answer itself stated the reported decrease. This is an annotation identity
failure, not proof of a missing outcome. Total time was 122.464 s: retrieval 11.985 s,
generation 86.367 s (including 62.717 s across two reviews), judges 24.099 s. One successful
question is not evidence of an overall improvement.

Runtime coverage v6 replaces copied effect quotations with native-enum IDs bound to unchanged
answer claims and resolved locally. Invalid annotations are distinguished from genuine
missing facts. Annotation-only correction uses the existing second review without an
answer rewrite; genuine content gaps retain one targeted repair. The total two-review
bound and all semantic/citation/numeric checks remain. This is an implemented correction,
not a measured live speedup: rerun q0046, then compare all four modes on the development
split. No historical artifacts, reviewed questions, models, caps or retrieval settings change.

Run `20261007T141338Z-3e482bff` received correctness/relevance 1.0 and retrieved/cited both
papers, but runtime marked it partial because the plan demanded an unrequested numerical
conversion and contained the protocol label `initial_searches` as a scientific requirement.
Grounding remained null/`unscored_needs_review` after invalid source-operation quotes and an
out-of-range claim index. Null is not a zero score. Total time was 145.333 s: retrieval
19.065 s, generation 89.066 s (including 53.064 s verification), judges 37.177 s.

Runtime v7 rejects standalone protocol labels through the existing native definition
correction and makes original-question coverage the sole completeness authority. Planner
gaps remain diagnostic; real requested facts still require verified essential support.
Judge v12 restricts method audits to native IDs bound to actual claims, retaining strict
own-source quote checks and the same correction limit. These general safeguards add no
normal-path calls or budgets. Offline tests verify contracts and bounds, not live quality
or speed: rerun q0046 before the full four-mode development comparison. Historical artifacts
and reviewed questions are unchanged; no re-indexing is required.

The later q0046 run `20261007T175042Z-86123102` completed without errors in 96.839 s
(retrieval 20.128 s, generation 66.253 s, judges 10.441 s), but correctness stayed 0.5.
Inspection found that retrieval stopped after a combined baseline/effect search and
substituted inner-radius insensitivity for the requested outer-radius outcome. The actual
outer-radius result was absent from the retrieved passages; full paper coverage was not
complete fact coverage. A malformed method audit copied source text instead of answer
wording, triggering an unnecessary content rewrite. This is a specific diagnosis, not proof
that the whole answer or all method attributions are correct.

Runtime v8 adds typed separate baseline/effect declarations, parameter-bound finish evidence
with bounded recovery, and unchanged-answer correction for annotation-only method failures.
Native answer review additionally records parameter/outcome spans and outcome classifications.
No historical results, reference answers, models, budgets or indexes change. Offline regressions
verify contracts and bounds; a fresh q0046 run and then the four-mode development split must
establish live quality and latency. Avoided rewrites may save time, while necessary recovery
can add a round; neither a speedup nor correctness improvement is guaranteed.

The last inspected q0046 run before the next baseline comparison,
`20261007T181832Z-77a6f650`, completed in 109.167 s (retrieval 13.228 s, generation
70.517 s, judges 25.410 s). Correctness was 0.5; grounding was null after invalid
method annotations, not zero or full support. The plan again combined the baseline
and outer-radius effect, declaring a null baseline index. Review selected the baseline
rate claim while naming the rate itself as the changed parameter; the requested
outer-radius result was absent from retrieved passages. A named membership algorithm
was also credited with a separate companion routine, despite a `not_applicable` audit.
Finding both papers did not establish either missing fact or method-role correctness.

Runtime v9 closes the null-baseline route for explicit coordinated requests and freezes
declared parameters into native review enums. Later planner calls use one frozen definition
snapshot; budget previews reduce repeated metadata and report blocked compaction attempts.
Method-role v3/judge v13 locally bind actual answer text and disallow waived audits for
explicit named-method cues. Own-citation support and existing repair/budget bounds remain.
These are generic offline-tested safeguards, not measured improvements. Rerun q0046, then
all four modes on development under the same judge policy; no re-index/new dataset is needed.

Run `20261008T111636Z-814ccd07` stopped before retrieval: both initial and corrective
definitions failed with the generic `invalid_effect_definition` code. It collected zero
chunks and ran no answer generation, yielding correctness 0. Total latency was 19.362 s,
not a pipeline speedup. `status: complete` denotes benchmark completion, not answer success.
The saved diagnostics omit the specific failing condition, so that condition cannot be
established retrospectively. Definition feedback now records indexed fields, distinct rule
codes and safe static correction messages, including query collisions after identity cleanup.
Offline tests replay valid/invalid plans through the native SDK with mocked transport;
live recovery remains unproven. Scope, correction bounds, models, budgets, indexes and
historical results remain unchanged. Rerun q0046 before the full development comparison.

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
