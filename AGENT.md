# RAG Demo — project handoff

## Purpose and current shape

This is a scientific-paper RAG demo: Streamlit (`src/chatbot_ui`) calls a FastAPI backend
(`src/api`), which retrieves from Qdrant and generates answers with OpenAI or Groq.
It supports source citations, figure retrieval, Redis-backed conversation memory, and
two ingestion modes. MkDocs documentation is in `docs/`; start at
`docs/architecture/index.md` for the fuller diagrams.

## Runtime architecture

- **UI:** `src/chatbot_ui/main.py`; sends `POST /rag2` and `POST /ingest` to `API_URL`.
- **API:** `src/api/main.py`; routers are in `src/api/api/`. Legacy `POST /rag2` requests
  classify questions and route metadata intents; explicit comparison modes bypass
  classification and retrieve evidence directly.
- **RAG:** `src/api/rag/modes/vanilla.py`, `hybrid.py`, `hybrid_rerank.py`, and
  `agentic/` own the four explicit retrieval strategies; `dispatcher.py` selects one-shot
  modes. `contracts.py` defines the explicit build scope
  and evidence provenance, while `tools/paper_search.py` and `tools/chunk_search.py` provide
  read-only PostgreSQL/Qdrant capabilities. `retrieval.py` owns shared embedding, prompting,
  generation and citation resolution. `sparse.py` creates deterministic BM25 sparse vectors;
  Qdrant applies IDF and RRF. Hybrid is dense+BM25+RRF; only Hybrid + Rerank adds Cohere.
  Generation emits atomic claims with exact cited chunk IDs and Agentic need IDs; the API
  returns this provenance, while the UI renders numbered citations per claim. Only those
  cited sources/figures are returned, and the benchmark grounding judge sees only each claim's
  cited excerpts (including paper/entity metadata). The Pydantic response model owns the strict
  OpenAI schema. `core/structured.py` uses native SDK chat/Responses `.parse` with those
  models, not manually serialized provider schemas; duplicate/unavailable citation IDs are rejected, with one bounded
  retry for malformed structured generation. Full paper titles quoted in the question also
  activate one-per-paper final selection in Hybrid + Rerank and one-citation-per-paper
  validation in baseline generation; citation coverage receives the same single retry.
  Agentic uses `modes/agentic/answering.py`: scoped citation integrity, model-assessed claim
  support and semantic requirement coverage, then at most one targeted repair. Preserve
  verified claims and disclose unsupported parts rather than dropping the entire answer.
  Evaluation judges use the same one-retry bound.
- **Memory:** pickled `ConversationMemory` objects in Redis, per `session_id`, 10-message
  recent window plus a Groq summary; TTL is refreshed to one hour on every message.
- **Uploaded-PDF ingestion:** PDF text/figures are extracted with PyMuPDF. Text chunks, a document summary,
  and figure descriptions become staged Qdrant points. Small uploads run synchronously;
  uploads of `INGESTION_BATCH_THRESHOLD` files or more submit figure analysis to OpenAI
  Batch. `src/api/papers/uploads.py` owns their shared catalogue lifecycle. The poller
  (`src/api/ingestion/poller.py`) finishes jobs from durable PostgreSQL manifests.
- **Storage:** local figures live under `src/api/data/images`; Azure Blob storage is selectable
  with `STORAGE_MODE=AZURE`. Local image URLs use `EXTERNAL_API_URL`.
- **Deployment:** `docker-compose.yml` runs UI, API, ingestion worker, and Redis. Qdrant is
  normally external (Cloud); the local Compose service is intentionally commented out.
  PostgreSQL is required by both ingestion paths and starts with the normal stack;
  only the one-shot arXiv CLI remains under the `papers` profile.

## Configuration and decisions

- `src/api/core/config.py` (`Config`) configures the existing API/RAG/upload stack;
  `src/api/papers/settings.py` (`PaperSettings`) configures the arXiv catalogue/CLI. Secrets and
  endpoints come from `.env`/environment; defaults in that class are intentional current
  defaults. Prompt templates are YAML files under `src/api/rag/prompts/`.
- `config.yaml` is currently **not loaded by `Config`**. Treat it as legacy/experimental until
  the code is changed to consume it; do not assume its collection or model settings are active.
- Generation provider is inferred from the model name (`gpt-*`/`o1-*` => OpenAI; Groq for
  `openai/gpt-oss-*` and other names), not from `GENERATION_MODEL_PROVIDER`.
- Public `ingest_documents.py`/`worker.py` entry points delegate to `papers/uploads.py`;
  the old implementations are retained as `_..._legacy` reference functions, not the
  app's ingestion path. `ingest_documents_old.py`, `ingest_documents_now.py`, `src/api/utils.py`,
  `evals/old/`, notebooks, and `docling_trial/` are experiments/legacy references.
- Preserve both corpora: arXiv uses `PAPERS_COLLECTION`, distinct from the uploaded-PDF
  `QDRANT_COLLECTION_NAME`. Ingestion may create collections, not a Qdrant Cloud cluster;
  the managed cluster must be provisioned separately.
- Current defaults are new dense+sparse collections: `arxiv_papers_v2` and
  `uploaded_papers_v2`. Never point the current writer at a dense-only collection. Migrate
  arXiv with `papers-reindex`; migrate uploads by re-uploading the original PDFs.

## Important current caveats

- `retrieval.py` uses the configured Redis host/port/database for local and Compose runs.
- New sync/Batch uploads share figure payloads (`page_number`, caption, year, build identity).
  Old indexed figures may still lack those fields; legacy adoption does not rewrite payloads.
- `ALLOW_ORIGINS` is documented but CORS is currently hard-coded to `*` in `main.py`.
- `main.py` mounts `config.IMAGES_FOLDER`, creating it if absent.
- The Makefile's `FRONTEND_IMAGE_NAME`/`BACKEND_IMAGE_NAME` values are reversed, so confirm
  actual image tags before building or pushing.
- `make docs-build` has existing missing-type warnings in `retrieval.py`.
  `make test` runs the offline pytest unit suite, not the legacy manual poller script.

## Useful commands

```bash
make compose       # local stack (recommended runtime path)
make docs-build    # validate/render MkDocs
make docs PORT=8001
make ingest        # legacy script: bypasses catalogue; do not use for the current workflow
make eval-preview  # Freeze active arXiv evidence locally; no model calls
make eval-rebase EVAL_FROM=... EVAL_DIR=...  # New snapshot; reuse reviewed questions
make eval-check EVAL_DIR=data/evaluation/gpt5  # Read-only model metadata access check; no inference
make create-eval-dataset  # Paid question generation from saved preview
make eval-run EVAL_DIR=data/evaluation/markdown-mini-v1 EVAL_LIMIT=2  # Paid RAG smoke benchmark
make langfuse-up   # Start this repo's optional self-hosted Langfuse v4 stack
```

Before changing behavior, trace the request through the router, RAG/ingestion module, and the
Qdrant payload fields together: retrieval and citation rendering depend on exact field names.

## Product direction and arXiv scope

The user's goal is a daily scientific-paper corpus and cross-paper querying, with
query-time comparison of Vanilla RAG and progressively more capable retrieval strategies
in Streamlit. Knowledge-graph RAG is a later milestone: do not add a graph database,
entity extraction or agent loop implicitly while maintaining the ingestion foundation.
The separate procurement RAG repository is an architectural reference, not the target
domain. PostgreSQL here serves paper identity, provenance and ingestion lifecycle;
it is not a reason to introduce procurement-style text-to-SQL tools.

### Current comparison modes and next milestone

`docs/architecture/rag-evolution-roadmap.md` is the source of truth for the next RAG
milestones. `docs/architecture/rag-modes.md` is the source of truth for what Vanilla,
Hybrid, Hybrid + Rerank, Agentic, KG and KG-Agentic mean and which are available. Read both with
`docs/operations/evaluation-results.md` before planning or changing retrieval. Follow the
roadmap order rather than jumping directly to graph storage.

Typed scope/evidence contracts, PostgreSQL paper discovery, scoped Qdrant search and separate
mode modules are implemented. Do not fold their logic back into one mode file.
Stable zero-based text `chunk_index` values are implemented in extraction artifacts,
manifests and Qdrant payloads under `markdown-structure-v2`; activation/audit verifies their
contiguity. A pilot/full reindex is still required wherever active builds use the older
pipeline. `tools/section_retrieval.py` and `neighbor_retrieval.py` now provide exact-section
and bounded ordinal expansion with strict paper/build scope. Never infer document order from
UUIDs. Agentic retrieval is implemented with LangGraph and native LangChain tools under
`modes/agentic/`: `graph.py` owns orchestration, `state.py` graph state, `tools.py` the four
read-only retrieval adapters, immutable requirement definition and terminal decisions, `policies.py` deterministic scope and
duplicate guards, and `executor.py` the pipeline adapter. `contracts.py` contains stable API
budget/execution contracts, not a provider-specific plan protocol. Preserve hard corpus,
round, tool, evidence, time and token limits. Scope escapes and zero-evidence stops fail
closed. When a bounded run already has scoped chunks, abstention, repetition, no-progress,
budget and later planner/tool failures terminate retrieval but use an `evidence_fallback`
into Agentic's reviewed answer generator; this avoids making the planner a second answer
gate. Resolve quoted full paper titles inside the bounded catalogue scope and ask the planner
to retrieve every resolved build. Missing builds/needs remain observable but may lead to
verified partial synthesis with explicit gaps, not automatic whole-answer abstention.
Agentic also resolves explicit arXiv ID/URL references, requiring a matching version when
specified. Confirmed full titles/IDs narrow initial and later queries to build filters;
partial titles/concepts cannot narrow scope. Measurements/sensitivities remain factual
needs within comparisons. Exact observed section headers may recover Markdown formatting,
not fuzzy or invented headings. Baseline mode resolution remains unchanged.
Search tool messages use 700-character previews with explicit truncation flags. Section/neighbour
expansion exposes full text within a 12,000-text-character per-response budget; neighbours give
the anchor priority. Native neighbour schemas enforce non-negative chunk ordinals and 0–5 per
side; before=after=0 reads just the anchor. Full artifacts remain unchanged for final generation. Execution metadata records synthesis policy and named-paper coverage. Do not recreate the
removed custom planner/provider schema layer. Add a
future KG retriever as another typed tool only after deterministic KG retrieval exists.

Agentic must call `define_requirements` once before searching; the graph freezes semantic
descriptions and assigns r1/r2/etc. Retrieval calls use these IDs as `need_id`; reformulation
cannot add requirements. The same native definition call supplies separate typed
`initial_searches` with queries/filters and 1-based `requirement_indices`, plus optional
`synthesis_indices`. Execute those explicit queries, never automatically copy descriptions
into searches. One search may cover multiple facts; synthesis tasks still receive final
answer review but require no mandatory search. Native `ToolNode` handles parallel initial
and later independent calls, with `AGENT_MAX_PARALLEL_TOOLS` (default 4, range 1–8) passed
through runnable `max_concurrency`. Dependent planner rounds remain sequential. Preserve
deterministic call-order merging, shared budgets and successful sibling results on failures;
do not replace native tool concurrency with a custom executor. Queries target requested facts,
with query/need IDs persisted in
evaluation output and Langfuse. `need_id` is excluded from duplicate fingerprints. Per-need
search coverage is diagnostic only: ANY scoped retrieved chunk may support ANY requirement.
Never reinstate per-search citation groups as answer-validation gates.
Initial searches normalize their associated needs to factual even if the planner labels
them synthesis-only. Planner/tool-schema guidance requires separate factual needs and focused
initial queries when BOTH a baseline measurement and parameter effect are requested; an
effect-only request must not acquire an unrequested baseline. This is semantic model guidance,
not a keyword classifier or hard decomposition guarantee. Recover only missing factual targets,
not the already established baseline. Do not mandate extra searches for derived comparisons. Confirmed bare
build UUIDs, like resolved full titles, belong in filters, not content queries. Remove an
eight-or-more-character UUID prefix only when it matches an already-filtered confirmed build;
never resolve/infer a filter from a prefix. For missing parameter effects, guide recovery toward
outcome + parameter + change/dependence passages rather than repeatedly reading settings/captions.
Do not inject expected values or mandate an analytic power law when an empirical effect suffices. Preserve
unknown identifiers; never infer a new filter merely from a UUID in user text.
An initial definition schema error receives one native ToolMessage error tied to the rejected
call ID, with whitelisted schema field paths/codes and no raw values. `requirement_validation.py`
also supplies static application-owned correction messages, never raw exception messages/context.
Parameter-effect rules have separate indexed codes (e.g. baseline_required,
parameter_not_in_question, baseline_effect_same_query), not opaque invalid_effect_definition.
Persist the same field/code/message in execution diagnostics and native correction feedback;
historical records without message remain readable. Check distinct content queries after
confirmed title/ID cleanup and whitespace/case normalization; changing filters/mode/limit
alone does not separate a baseline from its effect. Metadata-first and effect-only null-baseline
plans remain valid. Permit at most one
corrective definition call, charged to existing planner-token/time limits; freeze requirements
only after validation. Scope escapes, mixed tools, duplicate requirements and redefinitions
remain immediate hard stops. Persist requirement_validation_failures and actual
requirement_correction_attempts in execution/API/evaluation/Langfuse, including budget-blocked
or failed correction paths. No normal-path extra call, hidden retry, budget/model/default
change, schema rewriter, reindex or implicit paid trial. Graph recursion allowance includes
the two correction nodes without increasing retrieval rounds/tools.
Standalone protocol/tool labels (e.g. initial_searches, build_ids, get_neighbors) in
descriptions fail native Pydantic validation with internal_tool_requirement and use
that same one-correction path. Do not block scientific prose merely containing a field
name, silently delete/renumber entries, or add a classification call.
The native definition also records parameter_effects (literal original-question parameter,
effect requirement_index and nullable baseline_requirement_index). Declared baselines/effects
must have distinct factual indices and distinct initial queries; malformed/missing effect
declarations use the existing definition correction. Do not invent a baseline for effect-only
questions. finish_with_evidence requires effect_evidence for these needs: retrieved IDs,
contiguous parameter/outcome quotes and reported_change/reported_no_change classification.
Preserve qualifiers and signed numeric quote identity; settings, baseline or another
parameter cannot establish sufficiency. Rejecting a finish guides scoped recovery inside
existing budgets. At most two rejected finishes per round, and no recovery past max_rounds;
collected chunks remain eligible for reviewed partial synthesis. Persist parameter_effects
and effect_finish_checks in execution metadata/traces. Search-origin need labels remain
diagnostic, not citation allowlists. These native assessments are fallible, not semantic proof;
do not add expected values, new paid classification calls, automatic aliases or budget increases.
After freezing requirements, do not expose define_requirements again. On an over-budget
next-call reservation, `planner_context.py` supplies read-only query-focused tool previews
(400 chars/chunk, 6000 total), with truncation/deduplication flags and protocol IDs intact.
Recount before invocation; hard budgets still apply. Never mutate full evidence/artifacts
or interpret hidden preview text as missing source evidence. Execution/evaluation records
planner_context_compactions; no additional provider call or q-specific recovery is added.
Subsequent planner calls replace the completed definition call/result pair with one frozen
requirements/parameter snapshot, preserving the original question and all retrieval/error
pairs. Budget compaction removes repeated titles from chunk rows (retained once in a paper
catalogue); full evidence is unchanged. Record planner_context_compaction_attempts even when
the recounted call is blocked; planner_context_compactions counts invoked calls only. Never
loosen preflight when token counting fails.
Explicit coordinated measurement-plus-effect requests cannot declare a null baseline to
bypass distinct factual indices/queries. This grammatical routing hint is not an exhaustive
complexity/entailment classifier; effect-only questions must not acquire a baseline.
Freeze effect_parameters on validated AnswerRequirement records and propagate only literal,
applicable parameters into original-question checks. Native Pydantic parameter enums prevent
a reviewer substituting the measured output for the changed input. Original-question scope
and semantic support remain authoritative; no gold values or extra calls enter runtime.

Agentic's review checks each claim using only its cited excerpts, and actual answer coverage
against the question/requirements (values, units, ranges, uncertainty, comparisons). No gold
answers enter runtime review. One targeted repair preserves verified claims; partial output
names missing details. No verified claims means safe abstention. `generation_diagnostics`
records complete/partial/safe_abstention and per-requirement assessments in API/evaluation/
Langfuse. Model support checks are fallible; tests mock them and do not establish live quality.
There are at most two drafts and two reviews, each one provider call (60-second timeout,
configured generation-token cap, no provider retries), outside retrieval budgets.
Provider coverage uses Pydantic-generated required object keys for every frozen requirement
and original question part (lettered or numbered), not a free-ID list that permits omissions.
Normalize successful reviews to the existing public list format; record coverage_contract
frozen-parameter-effects-v9. Native coverage also requires essential_claim_indices (the minimal
subset of claim_indices supporting ALL user-requested facts) and specific missing_details.
Essential links must exist, belong to the declared coverage links and pass claim checks;
unknown links/empty essential support prevent completion. Rejected supplementary claims
remain diagnostic but cannot erase otherwise verified core coverage. Legacy adapters without
essential links conservatively treat all links as essential. Partial output names specific
missing_details, or local validation uncertainty, not the whole answered requirement.
When every original-question check is satisfied, omit rejected optional claims and
stop after draft+review instead of repairing unrequested background. Frozen plan coverage
is diagnostic, not another completeness gate. Review payload separates original_question_requirements
from planned_retrieval_requirements without duplicating their descriptions; completeness_authority
is original_question_parts. Persist planner_only_gaps and unplanned_requests as diagnostics,
never append them as mandatory gaps. Genuine omissions must be assessed under their original
q_ keys; repairs and displayed limitations are driven by those checks. A satisfied original
part still requires supported essential claims and the existing numeric/effect checks.
Never promote a partial
review merely because some claims survived, or relax semantic/numeric/own-citation gates.
Explicit parameter-dependence requirements additionally require
effect_status (reported_effect/test_settings_only/missing) and effect_claim_indices. Satisfied
effects require effect_outcomes selecting a native-enum answer_claim_id and
reports_requested_outcome=true. Freeze a0001/etc. anchors from the actual screened answer
claims; resolve IDs locally to unchanged answer_text and claim_index. Never use source text,
gold text, truncated or rewritten text as an answer anchor. Every effect link needs one
unique outcome audit, and at least one must be essential. ID selection proves identity,
not outcome relevance or support; those remain model-assessed. Test existence,
proposed tests or effects of a different parameter are not reported outcomes. No gold
values enter runtime and no additional review call is added. Historical/local quote adapters
retain strict quote identity; malformed audit wording is annotation uncertainty, not proof
of missing content. Persist answer_anchors and annotation_validation_failures per attempt,
effect_anchor_mode and annotation_correction_attempts. An annotation-only gap or failed review
may spend the existing second review on the SAME unchanged claims, without an answer repair.
Preserve previously verified claims; never auto-promote a verdict. Real content gaps retain
one targeted repair. Correction and content repair share the two-review limit: no third
review or later extra content repair. Unresolved annotations disclose validation uncertainty.
Native effect outcomes additionally bind requested_parameter (literal original-question name)
to answer_parameter_quote / answer_outcome_quote and outcome_kind. Preserve distinguishing
qualifiers; baseline/settings/other-parameter verdicts cannot pass an optimistic Boolean.
Malformed method claim/source quotes alone also use review-only correction when the claim
is otherwise supported, no numeric error exists, and every blocked essential link is an
annotation failure. Record invalid_method_annotation; do not auto-approve a real role
mismatch or request another content rewrite merely to repair audit wording.
Effects must link nonempty supported answer claims; baseline values, tested settings or an
absent formula do not answer an effect request. Qualitative effects can satisfy qualitative
requests without numbers/formulas. This is model-assessed semantics, not a keyword entailment
gate. Original-question checks apply even when the planner omits the effect. Preserve supported
partial answers and existing one-repair bounds. Missing/renamed keys use existing bounded repair/fail-closed handling.
Requirement descriptions remain in the review payload. Native OpenAI SDK `.parse` owns
schema serialization/normalization, including the $ref/description combination previously
rejected when sent as raw Pydantic JSON Schema. Do not add a custom schema-rewrite layer.
Offline tests exercise actual SDK HTTP serialization and required coverage keys; local
Pydantic validation alone is not evidence that the provider accepts a schema.
Live OpenAI answers/drafts/reviews use chat.completions.parse; synchronous benchmark judges
use responses.parse. The shared helper performs one request, normalizes safe failure codes,
and adds no retries. SDK transport retries are disabled; caller-owned repair limits remain.
Preserve refusal/length/incomplete-output handling, available usage/IDs and Langfuse parse
instrumentation. After a parse failure, usage_incomplete flags partial baseline/judge token
accounting rather than claiming zero paid usage. Instructor/Groq and typed LangGraph tools
remain unchanged. Background question generation retains its saved-ID polling/resume path;
never convert a queued job into a retrying synchronous parse request. No models, caps,
retrieval behavior, datasets or historical scores change as part of this standardization.
General citation repair supplies claim-specific missing values/units and supplementary
retrieved-chunk navigation hints, preferring the same paper and windows around missing
details (up to 8 rejected claims, 3 candidates each, 900 chars per excerpt/6000 chars total).
If a measurement and its condition are in separate chunks, prompt for both citations; if an
optional qualifier lacks support, remove that qualifier without dropping the supported fact
or hiding a user-requested gap. Never auto-attach candidate citations, relax numeric checks,
or treat a numeric match as semantic entailment. Repaired claims still undergo the same
independent review; no additional retrieval/model call or question-specific rule is allowed.
The first validation attempt records `citation_repair` diagnostics for candidate/missing-value
inspection in results and Langfuse.
Presentation-only normalization handles mathematical-font solar masses, braced inverse
units and attached Unicode scientific exponents; preserve signs, magnitudes and dimensions.
Approximation symbols bind an explicit spaced/Markdown sign to a following number, e.g.
∼−_ 1 _._ 75 becomes ∼-1.75 in the read-only validation view. Do not join ordinary range
separators/subtraction or infer missing signs. Wrong-sign/magnitude/uncited values still fail.
Malformed generated control characters fail screening with `invalid_control_character`
and use the existing repair. Never guess their glyphs or strip them into phantom values.
Stored chunks remain unchanged; retain citation-scoped numeric and semantic checks.
Clean abbreviated citation UUIDs from prose only when uniquely resolved within retrieved
context and distinguishable from bare numeric counts/ranges. Unknown/ambiguous UUID-like
abbreviations fail with unresolved_internal_citation_reference, not phantom numeric values.
Never auto-attach citations. Runtime ClaimCheck requires conditional typed method_attributions
in the native schema. Ordinary measurements/effects and unnamed routines use [] or not_applicable;
labelled future uses may use proposed_use. Those compact branches have no dummy method fields.
Reported named-method roles require applicability reported_operation, literal claim_quote,
short method name, claimed/source operation, status and own-citation quotes naming BOTH method
and operation. Record annotations naming methods absent from the actual claim as method_scope_issues;
do not let method:"[]" or a source-only method reject an ordinary fact. General support, numeric,
citation and coverage checks still apply. A proposal's reported method premises still need checks.
Actual role non-matches/invalid claim or own-source quotes override supported=true. Record
method_role_contract answer-bound-cited-operation-v3 and per-attempt checks;
semantic role equivalence remains a fallible model assessment, not a keyword proof.
Normalize letter-to-letter word hyphens only for quote presentation; retain numeric signs/values
and ellipsis markers. Never accept stitched/invented quote wording or change stored source text.
Use the native nested Pydantic union/SDK anyOf path, not a custom provider schema rewriter.
Native method audits resolve claim_quote locally from the selected actual claim index/ID;
copied source wording cannot replace answer identity. Historical quote adapters remain strict.
method_evidence.py supplies conservative literal named-algorithm/proper-name method cues,
not a method inventory or semantic proof. Expose reported_methods_to_audit to reviewers;
empty/not_applicable/proposed_use audits cannot waive these reported premises. Missing runtime
audits use existing content repair; missing grounding audits share its existing single
annotation/schema correction and otherwise remain unscored. Ordinary facts and clearly
labelled proposals retain independent support/numeric checks without an invented method gate.
Repair only missing details; preserve approved claims. Deduplicate whitespace/case-equivalent
claim text even with different citations/need IDs and record duplicate_claims_omitted. Never
fuzzy-collapse distinct conditions/values or change the two-draft/two-review bounds.
Surface-density validation recognizes equivalent g/cm² inverse-unit presentations and
does not mistake their -2 exponent for a measured value. A percentage-bearing fraction
does not require the noun "fraction" in a source supporting that percentage. Keep exact
values, dimensions, citation scope and independent semantic assessment; no q-specific rule.
Agentic synthesis prompts avoid repetitive/unrequested facts and verbose success feedback,
while retaining necessary evidence quotes and all requested details. Each validation attempt
records request stage_timings, including failures; generation_diagnostics totals draft/verify/
repair seconds, also exposed as agentic_*_seconds in benchmark timing summaries. They overlap
generation_seconds. No extra calls, smaller token caps, model changes or automatic paid tests.
AGENT_DRAFT_REASONING_EFFORT optionally controls compatible GPT-5 draft/repair calls only;
empty preserves provider defaults. It is independent of planner/verifier effort, ignored for
non-GPT-5 models, and recorded in manifests. Do not silently enable it or change baselines.
`make eval-run EVAL_DRAFT_REASONING_EFFORT=low` overrides it for the host process only;
omitted/empty Make values preserve Config/.env. Never launch a paid trial implicitly.
Vanilla/Hybrid/Hybrid + Rerank retain baseline named-paper gates and generation; baseline
citation retry exhaustion remains a scored safe abstention, not a benchmark exception.

Phase 7 is complete: Streamlit and the frozen-corpus runner expose Vanilla, Hybrid,
Hybrid + Rerank and Agentic; Langfuse receives the LangGraph model/tool/stop hierarchy and
separate Dataset Experiments. Benchmark results persist public Agentic execution metadata;
summaries aggregate stop reasons, synthesis policies, tool usage, rounds, evidence and
planner tokens, named-paper coverage and deterministic reviewed-paper coverage, and manifests
freeze the effective Agentic configuration. Correctness/relevance and groundedness use
separate judge requests so gold evidence cannot leak into grounding. Answerable abstentions are
scored incorrect deterministically; claim-level grounding checks source/entity attribution
against only the claim's cited chunks. New judging uses claim-role-bound-v13, retaining v8's
reference anchoring:
required per-question-part assessments, native-enum answer_claim_ids and required numeric values.
The runner freezes exact rendered claim spans plus remaining answer spans (including refusals/gaps),
assigns deterministic a0001/etc. IDs and resolves selections locally into answer_quotes for
numeric safeguards. Never use unrendered claims, gold text or retrieved text as answer anchors;
never truncate/rewrite resolved text or treat selection as proof of semantic correctness.
Answer/citation shapes remain unchanged; typed runtime/grounding method audits are separate.
Read the whole answer, not merely selected claims. Unknown IDs remain strict schema errors;
empty answered selections/duplicate IDs share the existing one-retry validation budget.
Persist judge.answer_anchors, per-check answer_claim_ids and reference answer_anchor_mode.
flagged_runs includes quote/anchor and semantic-consistency failures, even when repaired;
needs_review_question_ids records only unresolved conflicts. Historical runs remain unchanged.
Runtime review and both judges explicitly check method purpose, population and pipeline step;
sharing a paragraph or pipeline does not license assigning a separate method's operation.
Offline generic method-role fixtures test rejection/repair and prompt wiring, not live accuracy.
Grounding v12 uses a native enum of actual claim answer_claim_id values; the runner resolves
them locally to claim_index. Persist claim_anchors/answer_anchor_mode and require [] when
there are no claims. Unknown IDs and emitted numeric indices fail strict parsing and share
the same schema/annotation correction allowance; exhausted schema failures remain unscored_error.
Do not transfer reference answer anchors (which include other rendered spans) into grounding.
Historical index-based adapters remain readable. The conditional method audit retains independently extracted
source operations and own-citation quotes. Irrelevant method annotations are diagnostic scope
issues, not a gate for ordinary facts. Anchored declared actual-role mismatches cap groundedness
at 0.5; preserve raw_groundedness and method_validation_failures. Invalid claim/source quotes
or unknown claim indices are judge annotation failures, not proven answer defects: share
grounding's existing single schema retry, then leave groundedness null/unscored_needs_review
if unresolved. Persist annotation_validation_failures and grounding_consistency summaries.
No separate retry loop or reference/gold transfer into grounding is permitted.
Genuine missing facts or absent quoted target numbers cap scorable correctness at 0.5 with
observable safeguards; correct unanswerable refusals remain exempt from missing-fact penalties.
No gold facts enter runtime verification or the grounding judge. Preserve historical scores;
judge policy changes require fresh comparable runs, not retroactive edits.
Every reference check requires missing_or_incorrect_detail: nonempty for partial/missing/
incorrect, empty for answered. Native schema requires the field; contradictions in the
pairing are semantic review flags, not Pydantic parse errors. They share the existing one-retry schema/quote bound, never
auto-upgrade to full correctness. Prompts request a concrete expected-versus-actual deficit
and overall/per-check consistency; optional reference examples do not enlarge user scope.
Incorrect extra claims still affect correctness. Explained partials retain the same 0.5
cap; explanation presence is not semantic proof. Preserve gold isolation and historical runs.
Version 6 additionally requires deficit_basis (none/missing_content/incorrect_content/
reference_ambiguity) and claimed_missing_answer_fragments. Exact omission fragments found
in the whole answer and unresolved reference ambiguity share the existing schema/quote
single retry. Clear reference prose/captions for the same quantity/entity/case may resolve
damaged figure labels; never guess signs, invent unavailable text, or inject retrieved
evidence/grounding verdicts into reference judging. A thin reference is not proof that an
optional answer detail is false. Version 7 introduced leaving remaining semantic/quote conflicts unscored;
version 8 preserves that policy for semantic/anchor conflicts:
consistency_status needs_review, reference_score_status/score_status unscored_needs_review,
effective correctness null, raw_correctness in reference metadata. Preserve answer/evidence,
retrieval metrics, execution/generation diagnostics and timings; still run isolated grounding.
Skip numeric Langfuse correctness scores and reference abstention accuracy for unscored items.
Do not fabricate scores through correctness safeguards. Summary/profile metric_sample_counts
and report scored/unscored denominators make exclusions explicit; null is not zero or success.
Invalid JSON/types/missing fields/enums remain strict parsing failures with existing handling.
Judge transport or exhausted-schema failures preserve completed RAG outputs and deterministic
metrics; record separate judge_error stages with safe cause types, failed scores null and
score_status unscored_error. Keep valid independent-stage scores and known IDs/usage, marking
usage_incomplete where billing is unknown. Summary errors counts RAG failures, judge_errors
counts judging failures; manifest completed_with_judge_errors distinguishes them. Null scores
must not be converted to penalties/success by safeguards or Langfuse. In-flight item persistence
and judge-only replay are not implemented. Never claim a full benchmark rerun skips paid RAG work.
Semantic omissions/incorrect statements still receive normal penalties. Offline native-SDK
tests prove format, feedback, isolation and retry bounds, not live judge quality. No default
reasoning/model changes, historical edits, reindex or implicit paid trials.
Shared scientific range multipliers apply to both endpoints, without treating coefficients
as measured values. Answer anchoring recognizes explicit percentage-to-fraction equivalence
and whitespace/case-only quote differences. Legacy quote checks still reject bare counts,
changed numbers and stitched/ellipsis quotes; new provider outputs select IDs instead of copying text.
Anchor/quote-format correction shares the existing one-retry judge budget
with schema failures. Record quote_validation_failures, response IDs and available usage.
Native Pydantic numeric-target patterns permit only decimal strings; [] is the real empty
list, never ["[]"] or symbolic settings. Settings belong in requested_fact, not numeric targets.
Malformed schema feedback shares the existing one-retry budget; record schema_validation_failures.
Exhausted schema retries remain judge errors, not false correctness penalties. Judges assess
reported outcome effects independently of input settings; no gold facts enter runtime.
Runtime coverage records original-question-authority-v3: original user requests define mandatory
scope, not optional planner examples or paper-title words. Deterministic completeness-unit
checks intersect plan units with those explicitly requested in the question; independent
claim review still checks measurement units. Conceptual proposed cross-paper tests need
supported inputs and a clearly labelled linkage, not an unrequested quantitative conversion.
Do not present proposed relationships as paper-established results. No extra runtime calls,
retrieval changes, budget increases or historical-result edits are implicit in these fixes.
Hybrid + Rerank results
persist the complete Cohere candidate ordering for paper-diversity diagnosis. Preserve all four
as controls. The next slice is controlled Agentic development reruns and cross-paper
decomposition diagnosis. The agent must continue to
respect SQL-active builds and evaluation-frozen build IDs, retain chunk/page/section
provenance and receive no ingestion or mutation tools.

Expose the mode in Streamlit, trace plans/tools/budgets in Langfuse, and add it to the frozen-
corpus evaluator. Add cross-paper, human-written and corpus-level unanswerable questions and
paper-group development/held-out splits before final claims. Only afterward define and
prototype the scientific graph schema; expose deterministic KG retrieval separately before
combining it with the agent as `kg_agentic`. Do not run paid evaluations as implementation
tests. Implement and validate one roadmap slice at a time unless the user explicitly expands
the scope.

### KG milestone — first slice implemented

The user approved a provenance-first KG pilot, ultimately expanding to all eligible papers.
`docs/architecture/knowledge-graph.md` owns the concrete design and remaining phases.
Phase 8.1 adds `src/api/kg/` (typed extraction records and offline snapshot preview),
`pilot.json` (seven explicit paper IDs: M22 pair, omega Centauri pair, 47 Tuc pair and
connecting JWST survey) and opt-in `docker-compose.kg.yml` (pinned Neo4j Community,
localhost ports, persistent volumes). `make kg-preview`, `kg-schema`, `kg-up`, `kg-status`,
`kg-logs`, `kg-stop`, `kg-help` are available. Preview loads no configuration/.env, reads
no gold answers, connects to no services, writes nothing and invokes no model. Snapshot
selection is not live catalogue validation; sampled excerpts are NOT the full extraction
input. Missing pilot IDs fail explicitly; `KG_SELECTION=all` selects all snapshot papers.

Neo4j stores derived scientific assertions, not authoritative catalogue state. Preserve
PostgreSQL identity/active builds, Qdrant dense+BM25+RRF, existing point IDs, scoped citations
and all four modes. Source-reference validation checks identity/literal quotes only; it
does not establish entailment, alias validity, active scope or verified artifact hashes.
Build-local IDs must be namespaced by build/extraction revision in the future writer.
Keep conflicting measurements/conditions separate and hypotheses explicit. No global
fuzzy alias merge, guessed PDF numbers or arbitrary query-time writes/Cypher.

Phase 8.2 adds `kg-prepare`, explicit paid/resumable `kg-extract`, read-only `kg-validate`
and offline `kg-test`. `artifacts.py` reads exact frozen ready SQL builds (including retained
builds, excluding deleted papers) and hash-verified full text/pages/Markdown. No sampled
evaluation evidence or gold answers are extraction input. `jobs.py` freezes plan identity,
stores local SQLite per-attempt checkpoints, bounds call counts/concurrency and requires
explicit failed/interrupted retries; no hidden SDK retries or exact-once billing claim.
`extraction.py` uses `neo4j-graphrag==1.22.0`'s supported custom Component and Neo4jGraph
types with native SDK/Pydantic scientific parsing, not the default open-ended property
schema/JSON repair. Source IDs/page/section are application-bound; every quoted record
is validated against its full source chunk. `tracing.py` independently reuses optional
Langfuse settings without importing the API's eager global config. Dependencies are
optional (`uv run --group kg`). Local outputs are ignored under `data/knowledge_graph/`.
Model/settings/revision changes require a new directory; successes are reused only within
that directory. Empty scientific outputs are valid for boilerplate; scientific review is
still required. No live paid extraction has been run as an implementation test.

KG extraction diagnostics now retain specific rejection codes and zero-based record-field
paths in SQLite and `failures.json`, with concise terminal output. Never persist raw
exception/validation inputs or weaken exact-quote/endpoint checks to reduce failures.
Old generic failures cannot be reconstructed; explicit new attempts are needed for detail.
`KG_CHUNKS_PER_PAPER=N` selects a deterministic, body-preferred, distributed sample across
papers, interleaved fairly under `KG_MAX_CALLS`. N caps distinct attempted chunks per paper
over the output directory's lifetime (successes AND failures/interrupted count). Existing
plans/checkpoints remain compatible; no schema/prompt/model revision changed. Sampling
only selects pending chunks and cannot be combined with retry flags. `KG_FAILED_ONLY=true`
explicitly retries only failed/interrupted chunks; legacy `KG_RETRY_FAILED=true` still
includes pending work. No paid extraction/retries are authorized merely by implementing
or testing these features. `tests/unit/test_kg_selection.py` runs without optional libraries.

Next: review a bounded paid pilot, then staged graph persistence/activation. The experimental
builder must not replace extraction/chunking/embeddings. Its built-in Hybrid retriever is
Neo4j vector+full-text, not this repo's Qdrant Hybrid; preserve our search and add scoped
graph expansion. Graph activation, deterministic `kg`, `kg_agentic`, UI/evaluation support
and daily graph automation remain unimplemented. Do not claim graph queryability from
`kg-up` or `kg-preview`, or start paid extraction as an implementation test.
No reindex/evaluation regeneration is inherently necessary. For initial comparisons use
the same paper scope and subsequently pin graph extraction identity with frozen builds.

The user selected **star-cluster papers within `astro-ph.GA`**, not the whole category
and not an automatic expansion to `astro-ph.SR`. arXiv has no dedicated star-cluster
category. `ARXIV_CATEGORIES` AND any `ARXIV_TOPIC_TERMS` phrase in title/abstract define
the scope; cross-listed categories count. Defaults include star/stellar, globular,
open, young massive and nuclear star clusters. Empty topic terms broaden selection
to the whole category. Named-cluster-only papers can be missed; galaxy clusters are
not the same topic. Keep scope changes explicit and reviewable.

## Opt-in arXiv milestone: implementation and operations

`src/api/papers/` owns the unified PostgreSQL catalogue, versioned artifacts and a
text-only arXiv processing CLI. Default scope: `astro-ph.GA` AND star-cluster phrases
in titles/abstracts. See `docs/getting-started/arxiv.md` for commands and limitations.
Metadata settings are isolated in `PaperSettings` so discovery needs no model keys.
Use `python -m src.api.papers scope`, `init-db`, `backfill`, `sync`, `process`, `daily`,
or `status`. Nothing schedules paid ingestion automatically. Only the one-shot CLI
is in the Compose `papers` profile; existing uploads retain the legacy collection
but must be registered in PostgreSQL before they are queryable.

Explicit `/rag2` modes `vanilla`, `hybrid`, `hybrid_rerank`, and `agentic` bypass intent routing. `corpus=arxiv` filters
Qdrant to SQL-active builds; both sources support a corpus-change fingerprint. Streamlit
exposes these presets with isolated chat context. Hybrid is dense + BM25 sparse retrieval
fused with RRF; Hybrid + Rerank adds Cohere. Agentic can choose dense, sparse or hybrid
chunk retrieval and section/neighbour expansion. None is graph RAG.
Tests: `make test` (offline, including the frontend test; no paid calls).

### Storage and activation guarantees

- PostgreSQL is the catalogue/source of truth: `papers`, `paper_versions`,
  `paper_builds` (also the processing queue), and `paper_checkpoints`. Canonical paper,
  arXiv version and processing build IDs are distinct. Abstracts are source metadata,
  not generated summaries.
- Schema v2 renames `papers.arxiv_id` to `source_id` and adds `source` (`arxiv`/`uploads`).
  `papers-init-db` performs an idempotent migration preserving existing IDs/manifests.
  Upload identity is content-addressed: same bytes deduplicate, changed bytes are a new
  document, not a filename-based replacement. See `docs/operations/catalogue.md`.
- Build manifests record processing/model identity, artifact hashes/locations and
  verified point IDs/counts, vectors and payload identity. Only successful builds become active; failed replacements
  leave the previous active version queryable. Qdrant queries filter to SQL-active
  builds; old points are retained, not automatically deleted.
- `backfill` uses bounded submission-date Search API queries; `sync` uses incremental
  OAI-PMH metadata updates with pagination/checkpoints and overlap. Discovery queues
  work independently of PDF limits, preserving the backlog. Writes are serialized by
  a PostgreSQL advisory lock; retries are bounded by `ARXIV_MAX_ATTEMPTS`. Upload batches
  remain `waiting_batch` and unqueryable until all expected figures verify.
- Local PostgreSQL runs in its own `postgres` container, database `papers`, with
  persistent Docker volume `papers_postgres`. Host CLI: `localhost:5432`; Compose
  clients: `postgres:5432`. Do not treat container recreation as a database reset.
- Versioned PDFs/text use `data/paper_artifacts/` locally. Ephemeral deployments must
  use persistent storage, e.g. `PAPERS_STORAGE_MODE=AZURE` and a pre-created private
  `PAPERS_AZURE_CONTAINER`. This is separate from legacy figure `STORAGE_MODE` settings.

### Operator workflow

The following Make targets run the Python CLI on the **host**, except `papers-db-up`,
which starts PostgreSQL and waits for its health check. Merge settings into an existing
`.env`; never use `make env-file`/`make setup` to overwrite a configured environment.

```bash
make papers-help
make papers-scope
make papers-preview DAYS=7    # Metadata only; no DB connection/writes or embeddings
make papers-db-up             # Start PostgreSQL
make papers-backup            # Start local PostgreSQL if needed, dump and check its papers DB
make papers-backups           # List completed archives in ~/rag-demo-backups
make papers-init-db           # Create catalogue tables, not paper records
make papers-backfill DAYS=7   # Save matching metadata and queue pending builds
make papers-status
make papers-process LIMIT=2   # Explicit PDF download + paid embedding/indexing step
make papers-status
make papers-audit             # Read-only SQL/Qdrant consistency report; no repair/model calls
make papers-count             # Count documents with an active ready build (arXiv + uploads)
```

For an upgrade, quiesce ingestion and use `make papers-backup`; finish old Redis batches with the
previous worker, stop API/worker/UI, run `papers-init-db`, then
`make papers-import-uploads LEGACY_MODEL=text-embedding-3-small` (confirm the actual old
embedding model). Adoption records observed legacy vectors in SQL without touching
Qdrant or re-embedding. Run the audit and recreate API/worker/UI to apply new environment
and artifact-volume settings. Full rollout instructions are in the catalogue guide.

Backup helpers use host Python 3 (`scripts/papers_backup.py`) and Compose PostgreSQL
tools, not app/model dependencies. Default directory is outside the repo; override with
`BACKUP_DIR=...`. `papers-backup-check FILE=...` decodes the archive without executing SQL.
New archives are private, uniquely named and only published after a successful check;
failed attempts retain `.partial` files. These commands target local `postgres/papers`,
not `PAPERS_DATABASE_URL`, Qdrant, artifacts or Airflow state. No live restore, scheduled
backups, retention deletion or off-site copying is implicit. Archive checks are not
full restore rehearsals. See `docs/operations/catalogue.md#backup-commands`.

`pending` means catalogued but not yet searchable; `ready` means processing/indexing
succeeded. Inspect current status instead of assuming that "fetched" means embedded
or repeating historical paper counts from this discussion. `papers-sync` is metadata
only; `papers-daily LIMIT=10` syncs and processes **once**, not a scheduler installation.
`DAYS`/`LIMIT` overrides are optional; otherwise CLI/.env defaults apply. Preview and
backfill also accept `UNTIL=YYYY-MM-DD`. Containerized CLI and scheduling instructions
are in `docs/getting-started/arxiv.md`; the README links the quick-start sequence.

### Streamlit corpus selection and troubleshooting

- **Document inventory** defaults to **All sources** and calls `GET /catalogue?source=all`.
  It shows registered totals, latest states and whether an active build is compatible
  with the current collection. Inventory source selection is independent of **Query source**.
  Query source defaults to **All ready papers** and federates the separately scoped arXiv
  and upload collections. Legacy uploads remain visible but require re-upload into the
  current collection before retrieval. Upload acceptance is
  no longer displayed as completed ingestion. A failed replacement may retain an older
  ready build; latest-state counts and active-build counts can therefore overlap.
- `/documents` is a compatibility ready-upload listing backed by SQL; `/papers` lists
  active scoped arXiv builds. PostgreSQL/schema failure returns 503. The old ambiguous
  **Currently in database** button was removed. A 404 indicates stale/missing routes,
  not lost embeddings. Do not re-ingest papers to repair a listing.
- If a running bind-mounted API lacks a newly added route, `docker compose restart api`
  loads it; image-only deployments need a rebuild/redeploy. Refresh Streamlit and check
  the UI if you still see the old **Currently in database** button.
- Vanilla retrieves densely; Hybrid fuses dense and BM25 sparse candidates; Hybrid + Rerank
  adds Cohere; Agentic performs bounded adaptive retrieval. All use the same active corpus
  and grounding prompt.
  The corpus fingerprint detects changes; it is not a historical snapshot store.
  Use **Start new conversation** after ingestion changes active papers; it clears chat
  and the corpus fingerprint. **Refresh document inventory** only updates the listing.
  Corpus/mode/model changes isolate chat context; form submission prevents sidebar
  changes from silently repeating model calls.

### Verification and remaining limits

Use `make test` and `make docs-build`. The unit suite includes offline ingestion,
activation/citation/mode regressions, corpus-listing HTTP tests with mocked clients,
schema migration, legacy adoption, equal-count/wrong-ID drift, sync/Batch failure paths,
a Streamlit all-source inventory test, and Make dry-run tests. Some HTTP tests run handlers
inline because sandbox worker threads can stall; do not equate mocked HTTP coverage
with a real deployment smoke test. Never run paid ingestion as an implicit test.

`make papers-audit` compares active manifests to Qdrant, reports unregistered points,
and distinguishes retained old builds from incomplete jobs. It never repairs/deletes
or calls models. Nonzero can mean drift, concurrent changes or an operational error;
rerun in a quiet window before repair. Legacy adoption establishes an observed baseline,
not proof of complete historical PDF extraction or the original embedding model.

Check live PostgreSQL readiness, `/catalogue`, `/papers` and the Qdrant collections separately
when debugging a deployment; `/health` currently checks Redis/Qdrant, not PostgreSQL.
Both arXiv and uploads use `papers/extraction.py`: pinned PyMuPDF/PyMuPDF4LLM 1.27.2.3,
OCR disabled, per-page Markdown, section-aware chunks capped at 512 cl100k_base tokens,
up to 64 tokens of whole-paragraph overlap, complete table rows and repeated headers.
Tables that cannot retain complete rows become explicitly labelled `table_unstructured`
evidence rather than being dropped. Text chunks carry a zero-based, contiguous `chunk_index`;
summaries and figures do not. Mathematical fidelity is not guaranteed. Figures remain handled separately on the upload path; arXiv has no figure
enrichment or graph extraction. Versioned artifacts include Markdown/pages/chunks and SPEC.
Extraction/chunking changes must bump SPEC and therefore pipeline identity. New upload
registration only deduplicates an active build of the current pipeline, so the same PDF
bytes can upgrade an old extractor without changing its paper identity.
`make papers-extractor-setup` prepares the public tokenizer vocabulary cache in the venv
for offline operation; backend/Airflow builds bundle it. `papers-extract-preview PDF=...
EXTRACT_DIR=...` is a local-only, no-overwrite inspection tool. `papers-reindex-preview`
is read-only; `papers-reindex LIMIT=...` explicitly incurs PDF downloads and embeddings
for existing active scoped arXiv papers, not discovery backlog. It preserves old active
builds until verification, scans active old collections, skips already upgraded papers, and
honors attempt limits.
Uploads upgrade through re-upload (including paid figure/metadata work). Never launch
paid re-indexing as an implementation test. Pause/drain old workers and rebuild API,
ingestion worker and Airflow together; old saved daily plans cannot cross pipeline changes.
After re-indexing, generate a fresh evaluation snapshot or use `eval-rebase` to preserve
reviewed questions. Rebasing compares complete old/new text streams and scientific metadata,
retains approval only for exact papers, downgrades drift to `needs_review`, clears splits and
never overwrites its source/output. Keep old Qdrant points until rebasing finishes. Never
rewrite old preview hashes.
Migration v1→v2 is implemented; a general migration framework, operator retry/reset,
ambiguous remote-Batch submission recovery, interrupted-upload recovery, stale-build cleanup and
historical snapshot serving remain follow-ups; see the guide for detailed limitations.

## Evaluation question generation

`evals/generate_questions.py` provides `prepare`/`generate`; see
`docs/operations/evaluation.md`. The Make target `create-eval-dataset` uses this local
generator. Preview freezes
manifest-listed active evidence with identity checks and deterministic sampling.
Defaults: up to 50 scoped arXiv papers, four text excerpts each, 30 single-paper /
15 cross-paper / 5 insufficient-evidence candidate jobs, `gpt-4.1-mini`.
New plans also carry a retrieval profile (`single_fact`, `single_synthesis`,
`cross_comparison`, `cross_multihop`, `metadata_discovery`, or `unanswerable`). The
Agentic-ready v3 recommendation is a new 70-question directory over 50 papers with
counts 20/10/15/10/5/10 respectively. Configure these through the corresponding
`EVAL_*` Make variables documented in the evaluation guide. Cross-paper planning uses
topic-related disjoint pairs before reuse so paper-group splits remain feasible.
`EVAL_MAX_TOKENS` / `prepare --max-completion-tokens` sets the per-call reasoning +
answer budget (default 2500, range 256–128000). It is frozen in the plan, not overridden
at generation time. The documented GPT-5 example uses 25000 in a new `EVAL_DIR`;
existing previews and completed checkpoints remain compatible without changing hashes.
Generation uses Responses API background mode (`evals/background.py`), strict JSON schema,
and the saved cap as `max_output_tokens`. Requests use `store=false`, but background mode
still temporarily stores response data server-side (roughly ten minutes; see linked
OpenAI guidance in the evaluation guide). HTTP timeouts are at most 20 seconds, polling
every five seconds, with a per-job 600-second wait budget (`EVAL_WAIT_SECONDS`, 5–3600).
An interrupted or timed-out poll does not cancel the remote job.
`eval-check` reads the saved model's metadata with a 20-second timeout and no inference
or local writes. It uses the same API credentials/endpoint as generation; success is
not proof that long generation calls will succeed. Safe diagnostics expose exception
types and numeric codes, never raw exception text/headers/URLs/keys. Failed generation
requests also write `last_error.json` (job ID/time/elapsed/cause category), without marking
that job complete or changing earlier checkpoints. No automatic retries were added.
Generation is explicit paid work; never run it as an implicit implementation test.
Persist a submitting marker before POST and the returned response ID before polling in
`results.json`; terminal output is cached before validation. Known IDs resume through GET,
not another paid POST. Unknown submission outcomes, expired IDs and terminal failures
require explicit `RETRY_JOB=<id>` authorization after review; archive old attempts.
Never promise exactly-once billing when a submission response is lost. Completed responses
(including legacy rejections) are skipped; new results record the background transport.
Local output defaults to git-ignored
`data/evaluation/star-clusters`. New samples require a new `EVAL_DIR`.
Profile labels must remain attached through review, local results, Langfuse and run
manifests. They are evaluation strata, not proof that a generated question truly has
the claimed difficulty; human review must verify synthesis/multihop requirements.
Generated unanswerable items remain excerpt-scoped until a reviewer searches the frozen
corpus, and independent human-written questions must be added manually.

## Evaluation runner and Langfuse

`evals/run_benchmark.py` consumes only `review_status=approved` records from a separate
`questions.reviewed.json`. It validates the sibling snapshot hash and embedding model, then
queries the exact frozen Qdrant build IDs rather than the current active catalogue. Each
invocation creates a unique checkpointed directory under `data/evaluation/runs/` with a
manifest, per-item results, aggregate JSON and Markdown report. All four modes use the same
questions, generation model, top-k and frozen scope. `EVAL_JUDGE=true` adds explicit
paid Responses API judge calls. Partial item results survive interruption, but benchmark
resume is not implemented; a retry is a new run. Never run a benchmark implicitly during tests.
Benchmark judges read EVAL_JUDGE_MAX_OUTPUT_TOKENS from Config/.env (default 16384,
range 256–128000), replacing the old hard-coded 1200. It applies per reference/grounding
request, including reasoning and JSON, independently of generation/runtime-verifier caps.
Preserve the single retry bound and do not escalate the cap automatically. Record
judge_max_output_tokens in manifests and max_output_tokens in successful judge metadata.
This is headroom, not guaranteed completion or a total-run spend cap; complex cases may
need an explicitly configured 32768. Host make eval-run needs no container rebuild.

Historical reviewed schema v1 remains runnable only as `split=all`. New schema-v2 review
files are validated by `evals/review_dataset.py`: approved items require reviewer/source
checks, approved negatives require verified `frozen_corpus` scope, and deterministic split
assignment keeps connected paper components wholly in development or test. Use
`make eval-split`, then `make eval-validate`; `make eval-run EVAL_SPLIT=development|test`
records both the complete dataset hash and exact selected-question hash.

Langfuse v4 is the sole supported observability integration and runs as an opt-in,
repository-owned Docker stack in `docker-compose.langfuse.yaml`. Host processes use
`LANGFUSE_BASE_URL`; application containers use `LANGFUSE_BASE_URL_CONTAINER`. All imports
go through `src/api/observability/tracing.py`; it is a true no-op when disabled. OpenAI clients
for the active query path come from `src/api/core/clients.py` so calls are auto-instrumented.
With Langfuse enabled, the runner syncs a content-addressed, idempotent Dataset and records
each mode as a Dataset Experiment, while local files remain authoritative. Use a separate
Langfuse project for this repository. `make langfuse-stop` preserves its named volumes.
The local Compose deployment has no high availability or automatic backup policy.
Frozen build IDs constrain eligible points, but Qdrant BM25 IDF remains collection-wide;
pause ingestion or use a cloned collection for final repeatable sparse-mode comparisons.
All candidates need human review; quote/ID checks do not prove scientific entailment.
New previews apply `evals/quality.py` evidence heuristics: exclude references, acknowledgments,
funding, citation lists and empty placeholders; prefer Methods/Results/Discussion/Conclusions.
New plans freeze `quality_policy: fact-first-v1`: require full paper titles and reject explicit
missing-information answers for answerable jobs. Old plans retain prior validation; never
rewrite their hashes or checkpoints. These gates do not establish scientific entailment.
Negatives are excerpt-scoped, not proven absent from the entire corpus. Cross-paper
pairing uses lexical metadata overlap, not KG reasoning. `make eval-run` consumes the
reviewed format. Schema-v1 datasets have no defensible held-out split.
Do not change ingestion, retrieval presets or add graph infrastructure as part of
maintaining the question generator or benchmark runner.

## Optional daily orchestration

- `src/api/papers/schedule.py` is scheduler-independent; `schedule_store.py` persists
  daily state in additive `paper_daily_runs` (created by `papers-init-db`; schema v2
  remains compatible). One immutable plan per actual UTC day, fixed build IDs and
  persisted per-build attempt reservations before paid work. No refilling on retries.
- `make papers-scheduled LIMIT=10` explicitly runs discovery/process/audit/report once;
  `make papers-run-status [RUN_DATE=YYYY-MM-DD]` only reads state. Legacy `papers-daily`
  and `papers-process` remain outside this scheduled budget. Do not run both schedulers.
- `dags/arxiv_daily.py` targets Airflow 3: 07:15 UTC, catchup false, one active run/task,
  paused on creation, one retry/task, two-hour task timeouts. Audit/report use all_done;
  report fails on unsuccessful upstream stages, so an audit cannot mask ingestion failure.
- `PAPERS_RUN_MAX_ATTEMPTS` defaults to two per selected build/day, also bounded by the
  lifetime build attempt budget. Interrupted attempts count. No exact dollar/token cap.
  Paid daily stages reject historical dates; retries crossing midnight fail for review.
- Monitoring is optional locally by explicit user choice: `PAPERS_REQUIRE_MONITORING`
  defaults false. Empty `PAPERS_ALERT_WEBHOOK_URL` / `PAPERS_HEARTBEAT_URL` log warnings
  and persist notification status `skipped`, never `sent`. Missing optional endpoints
  do not block successful ingestion/reporting; actual ingestion/audit failures still fail.
  Configured HTTPS endpoints are used (failure JSON POST / success GET); delivery errors
  still fail reporting. Set the strict flag true to require both URLs before processing.
  Without an external heartbeat monitor there are no missed-run/host-outage alerts.
  Notifications are at-least-once; URLs are secrets. Strict-mode errors name the required
  settings without exposing values. Rebuild/recreate Airflow to apply code/env changes.
- Optional Compose `airflow` profile uses a pinned Airflow image, an isolated app venv,
  and separate orchestration PostgreSQL. `make airflow-up` never unpauses a new DAG;
  restarting a previously enabled DAG preserves its enabled state. Do not enable live
  schedules, send test alerts or invoke paid ingestion implicitly as implementation tests.
- The standalone service is localhost-only development infrastructure, not production
  Airflow. Docs: `docs/operations/daily-ingestion.md`. Tests use offline DAG/API doubles;
  `make airflow-check` inspects actual import errors after building without running tasks.
