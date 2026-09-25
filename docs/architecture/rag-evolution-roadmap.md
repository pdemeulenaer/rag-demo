# RAG evolution roadmap

## Goal and current baseline

The product goal is to compare increasingly capable RAG strategies at query time over the
same scientific-paper corpus. The Streamlit UI and evaluation runner must preserve explicit,
independently selectable modes so improvements can be attributed to retrieval architecture.

Current modes:

- **Vanilla:** dense Qdrant retrieval, then answer generation.
- **Hybrid:** dense and BM25 sparse retrieval, reciprocal-rank fusion, then generation.
- **Hybrid + Rerank:** Hybrid retrieval, Cohere reranking, then generation.
- **Agentic:** a bounded LangGraph agent selects dense, sparse, hybrid and expansion tools.

The first reviewed benchmark found Hybrid stronger on retrieval coverage, correctness,
groundedness and relevance, while gold-citation recall remained approximately 0.43 in both
modes. That run predates the current BM25 index and mode split; see
[Evaluation results](../operations/evaluation-results.md). The next milestone is a new
four-mode benchmark on the dense+sparse corpus, followed by knowledge-graph retrieval as an
additional evidence tool for the same orchestration layer.

## Design rules

1. Keep the four explicit mode pipelines separate and stable as experimental controls.
2. Put retrieval capabilities behind typed, directly testable, read-only tools before adding
   an LLM-driven graph loop.
3. PostgreSQL remains authoritative for paper/build identity and metadata; Qdrant remains
   authoritative for searchable chunk vectors. Tools may combine them but must respect
   SQL-active or evaluation-frozen build IDs.
4. Every returned fact must retain paper, build, chunk, page and section provenance.
5. Bound agent iterations, retrieved context, tokens and wall time. A default maximum of
   three retrieval rounds is the starting policy.
6. Trace plans, tool calls, retrieved evidence, model use, latency and failures in Langfuse.
7. Do not perform paid model calls in automated unit tests.
8. LangGraph is the Agentic workflow framework, not a scientific knowledge graph or graph
   database. Do not introduce KG storage merely to anticipate KG-RAG.

## Phase 1 — shared retrieval foundation

Implementation status:

- complete: shared `RetrievalScope`, `PaperMatch` and `EvidenceChunk` contracts;
- complete: PostgreSQL `search_papers` and scoped Qdrant `search_chunks`;
- complete: separate Vanilla, Hybrid and Hybrid + Rerank modules using the shared scope boundary;
- complete: versioned BM25 sparse vectors with Qdrant IDF and RRF fusion;
- complete: Agentic chunk search can select dense, sparse or hybrid retrieval.

Implement framework-independent functions with typed inputs and outputs:

| Tool | Store | Purpose |
| --- | --- | --- |
| `search_papers` | PostgreSQL | Resolve papers/builds by title, author, year, source and metadata terms |
| `search_chunks` | Qdrant | Run dense, sparse or Hybrid search within explicit build/paper filters |

Tool results must use a shared evidence model and must not return unregistered or inactive
builds. For frozen evaluations, they must be constrained to the snapshot's build IDs.

## Phase 2 — stable chunk ordering

Implementation and active-corpus rollout are complete. Extraction specification
`markdown-structure-v2` assigns every textual chunk a zero-based, contiguous `chunk_index`.
The ordinal is stored in `chunks.json`, the build manifest and Qdrant payload. Summaries and
figures are intentionally outside this ordering. Activation and audit validate the contract,
and the required integer/keyword payload indexes are created during indexing.

Never infer document order from Qdrant UUIDs. An installation is ready for Phase 3 only when
`papers-reindex-preview` reports zero upgrades and `papers-audit` is healthy.

## Phase 3 — evidence expansion tools

Implementation status: complete as read-only tools and exposed through the Agentic mode.

| Tool | Store | Purpose |
| --- | --- | --- |
| `get_section` | Qdrant | Retrieve ordered chunks from one exact paper/section breadcrumb |
| `get_neighbors` | Qdrant | Retrieve a bounded ordinal window around a promising text chunk |

Both tools require an explicit paper/build pair, compose the active or frozen Qdrant scope,
validate every returned identity, require stable chunk ordinals and return `EvidenceChunk`.
Section reads are capped at 50 chunks. Neighbour reads are capped at five chunks per side.
They have Langfuse retriever spans and deterministic offline tests for ordering, empty
sections, bounds and scope violations.

Exit criteria:

- deterministic offline unit tests cover filters, empty results, invalid identities and
  scope enforcement;
- current one-shot pipelines can use the shared primitives without scope/provenance drift;
- each tool has a Langfuse span and returns complete evidence provenance.

## Phase 4 — typed tools and execution contracts

Implementation status: complete and incorporated into the LangGraph runtime.

Each read-only operation has its own small LangChain tool schema: `search_papers`,
`search_chunks`, `get_section` and `get_neighbors`. Two terminal tools express the evidence
decision: `finish_with_evidence` and `abstain`. A native `define_requirements` tool records
the requested facts once before retrieval; it does not access external data. `contracts.py` contains the stable public
budget and execution metadata used by the API/UI; `state.py` contains internal graph state.
There is deliberately no provider-specific union of plan/action/assessment JSON schemas.

Unknown tools and malformed arguments are rejected by native tool validation. Deterministic
policy code separately enforces corpus scope, duplicate-call detection and hard limits for
rounds, tool calls, evidence, elapsed time and model tokens. No ingestion, deletion,
database mutation, shell or arbitrary-code tool is exposed.

## Phase 5 — bounded Agentic RAG mode

Implementation status: complete as the API/runtime milestone. Streamlit exposure was added in
Phase 6; benchmark exposure was added in Phase 7.

The explicit `agentic` mode uses LangGraph tool calling followed by reviewed synthesis:

1. Classify whether the question needs one paper, multiple papers or metadata discovery.
2. Call `define_requirements` once; freeze requested facts with graph-assigned r1/r2/etc. IDs.
3. Select tools and explicit paper/build filters.
4. Assess evidence sufficiency after each retrieval round.
5. Reformulate or narrow an unsuccessful search when useful.
6. Generate claims from accumulated evidence, review support and completeness separately,
   then repair at most once while preserving verified claims and disclosing missing details.

Every retrieval call has a required atomic `need_id`. Chunk searches must use a focused
query for one requested fact rather than the complete multi-part question; distinct facts
from the same paper require distinct searches. Execution records persist the actual bounded
lookup query next to the need ID so evaluation can inspect decomposition without relying on
private reasoning. Calls must reuse IDs from the frozen requirements; searches cannot add
mandatory answer requirements. Per-need retrieval coverage is diagnostic only, not semantic
entailment or a citation allowlist. Any scoped chunk may support any requested fact.
Catalogue-only discovery actions are routing steps, not answer evidence.

The loop terminates after at most three retrieval rounds by default (operators may select up
to five for controlled experiments). It must also stop
when evidence is sufficient, the budget is exhausted, or repeated searches add no new
evidence. Insufficient evidence must produce an explicit abstention rather than an invented
answer. The agent receives read-only corpus tools; ingestion, deletion and database mutation
are outside its authority.

The planner is not a second answer-generation gate. If a bounded run stops because of an
explicit planner abstention, repetition, no progress, a budget, or a later planner/tool error
after it has already collected scoped chunks, those chunks continue to Agentic's reviewed
generator. The generator may answer only what they support and must explicitly
state that a requested detail is missing. A stop with zero collected evidence remains a hard
abstention. Execution metadata distinguishes `model_finish`, `evidence_fallback` and
`hard_stop` synthesis policies.

For questions that explicitly quote full indexed paper titles, a deterministic catalogue
step resolves those titles inside the active/frozen scope. Their build IDs become required
coverage. The planner receives the authoritative IDs, searches each independently (parallel
tool calls are allowed). Missing required builds prevent a sufficient-evidence finish but do
not prevent verified partial synthesis via evidence fallback. The answer must disclose gaps.
Chunk search gives the planner 700-character previews with truncation flags. Targeted section/
neighbour expansion exposes full text within a 12,000-text-character response budget; neighbour
reads prioritize the anchor and expose the 0–5 per-side bounds in the native tool schema.
Full evidence remains unchanged for Agentic synthesis and cited excerpts for its support review.

This is intentionally a constrained retrieval agent. Merely asking an LLM to choose between
the existing Vanilla and Hybrid functions, without decomposition, evidence checking or
iterative retrieval, does not satisfy this milestone.

Implemented safeguards and exit criteria:

- `POST /rag2` accepts `mode: "agentic"` and returns the selected mode, corpus fingerprint,
  ordinary verified citations and concise `execution` metadata;
- the executor intersects every action filter with the immutable active/frozen corpus scope;
- at most three rounds run by default, with independent tool-call, evidence, elapsed-time and
  agent-model-token limits;
- repeated actions, repeated evidence, two empty-result rounds, tool failures, model/schema
  failures and explicit insufficiency terminate retrieval; any already collected evidence is
  still eligible for the same grounded generator used by the other modes;
- direct questions can synthesize after one retrieval round and a terminal tool call;
- tool calls without an atomic need ID fail before execution, and duplicate-action detection
  ignores the need label so an identical lookup cannot evade the repetition guard;
- offline tests cover termination, scope escape, repeated actions, tool failure, abstention,
  malformed model output and native tool schemas.

The implementation is isolated in `src/api/rag/modes/agentic/`: `graph.py` owns LangGraph
orchestration, `state.py` its state, `tools.py` the LangChain adapters, `policies.py` the
deterministic guards, and `executor.py` the small pipeline adapter. `answering.py` owns
Agentic-specific synthesis: scoped citation IDs, model-assessed grounding using each claim's
own cited excerpts, and semantic completeness against the question and frozen requirements.
Need labels and values found only in evidence are not proof of an answered fact.
One targeted repair preserves verified claims; remaining gaps yield a partial answer rather
than whole-answer abstention. No verified claims means safe abstention.
See [Agentic answer checks and repair](rag-modes.md#agentic-answer-checks-and-repair) for
call limits and diagnostic fields. This adds verification cost; it does not change baseline
generation or require re-indexing/new evaluation questions. Live improvement is unproven
until a controlled development rerun.

## Phase 6 — API, Streamlit and observability

Implementation status: complete.

Streamlit exposes **Agentic** alongside **Vanilla**, **Hybrid** and **Hybrid + Rerank**. The existing comparison
key isolates chat state by corpus, mode and answer model while preserving the corpus
fingerprint across mode switches for fair comparisons. Each Agentic answer has a collapsed
execution panel containing only the validated plan summary, outcome, rounds, successful tool
counts, papers touched, evidence count and elapsed time. It does not expose prompts, evidence
text or hidden reasoning. Existing source and figure rendering still uses verified citation
IDs.

Langfuse receives the safe execution hierarchy: `rag_request` → `rag_pipeline` →
`agentic_retrieval`, plus LangGraph/LangChain model and tool callbacks, existing retriever
spans and Agentic draft/review/repair generation spans. Tool calls, evidence IDs, budget usage, stop reason,
model usage and latency are recorded without exposing private reasoning. Tracing remains
optional and cannot change request behaviour.

## Phase 7 — evaluation

Implementation status: runner/Langfuse mode integration, named-paper coverage enforcement,
paper-coverage metrics and core agent execution aggregates are complete. Controlled reruns
and estimated cost remain.

The runner accepts all four modes using the same reviewed questions, frozen builds, answer
model and top-k/context policy wherever comparable. Each selected mode is a separate
Langfuse Dataset Experiment. Old dense-only snapshots remain historical and must not be
rewritten; create a new reviewed snapshot after the v2 re-index.

The runner now records these agent-specific measures locally and in Langfuse:

- retrieval/tool rounds and repeated-action stops;
- evidence coverage and citation recall;
- required-paper retrieval/citation coverage and missing named papers;
- per-action tool usage (for diagnosing cross-paper decomposition);
- correct abstention when evidence remains insufficient;
- latency and planner token usage. Estimated model cost remains a follow-up.

Run a small smoke evaluation first, followed by the full development set. Do not declare an
improvement from judge scores alone; inspect per-question regressions and retrieved evidence.
Correctness/relevance and groundedness use separate judge requests: grounding receives no
reference answer or gold evidence.

If baseline answer generation still produces invalid or incomplete citations after its one
bounded repair retry, the pipeline returns a safe abstention while retaining retrieved
chunks and structured generation diagnostics. Evaluations therefore record a scored
abstention rather than losing retrieval evidence as a runtime error.

For questions containing quoted full paper titles, Hybrid + Rerank reserves one final
candidate per named paper before filling the remaining top-k positions. Baseline generation
then validates that at least one chunk from each named paper was cited and permits one
bounded corrective retry. Complete Cohere candidate rankings remain recorded so this guard
can be evaluated rather than assumed beneficial.

### Strengthen the evaluation set

Before tuning or presenting final comparisons:

- use the profiled v3 plan in the evaluation guide to distinguish direct facts,
  within-paper synthesis, cross-paper comparisons, cross-paper multihop, metadata
  discovery and unanswerable cases;
- add more genuinely multi-paper questions;
- approve corpus-level unanswerable questions that test abstention;
- include several human-written research questions to reduce synthetic bias;
- create development and held-out splits at paper/group level to prevent leakage;
- repeat final runs or bootstrap item-level differences to quantify uncertainty.

Use the development split while implementing. Reserve the held-out split for milestone
comparisons.

## Phase 8 — knowledge-graph RAG

### Graph construction

Define a scientific schema before selecting infrastructure. Candidate entities include
papers, authors, astronomical objects, instruments/datasets, methods and reported
measurements or claims. Relations and extracted values must link back to the exact source
build/chunk/page and record extraction model/version and confidence.

Build the graph offline and incrementally as paper builds activate. Normalize aliases and
units, retain conflicting claims instead of overwriting them, and validate entities and
edges before making them queryable. Graph activation should follow the same replacement
safety principle as vector builds.

Choose graph storage after testing the required traversals. PostgreSQL tables/recursive
queries minimize infrastructure for a small graph; a graph database is preferable when the
demo needs expressive multi-hop traversal and graph-native inspection. The decision should
be recorded separately and must not make PostgreSQL/Qdrant provenance ambiguous.

### Graph retrieval and comparison

Expose graph search/traversal as another typed evidence tool. First evaluate a deterministic
`kg` retrieval mode, then allow the agent to combine vector, metadata and graph tools as
`kg_agentic`. The final UI/evaluation matrix should be:

| Mode | Adaptive tool use | Graph evidence |
| --- | --- | --- |
| Vanilla | No | No |
| Hybrid | No | No |
| Hybrid + Rerank | No | No |
| Agentic | Yes | No |
| KG | No | Yes |
| KG-Agentic | Yes | Yes |

This separation is important: it distinguishes gains from graph structure from gains caused
by iterative planning.

## Recommended implementation order

Complete one reviewable slice at a time:

1. shared retrieval foundation (complete);
2. stable chunk ordering and reindex (complete);
3. section/neighbour evidence expansion (complete);
4. native typed tools and public execution contracts (complete);
5. bounded LangGraph tool loop with an API-only `agentic` mode (complete);
6. Streamlit mode and Langfuse trace presentation (complete);
7. benchmark integration (complete), then fresh evaluation-set strengthening and runs;
8. graph schema/provenance, deterministic KG retrieval, then KG-Agentic composition.

Do not start a later slice while an earlier slice lacks offline tests, provenance guarantees
or evaluation compatibility.
