# RAG evolution roadmap

## Goal and current baseline

The product goal is to compare increasingly capable RAG strategies at query time over the
same scientific-paper corpus. The Streamlit UI and evaluation runner must preserve explicit,
independently selectable modes so improvements can be attributed to retrieval architecture.

Current modes:

- **Vanilla:** dense Qdrant retrieval, then answer generation.
- **Hybrid:** reciprocal-rank fusion retrieval, Cohere reranking, then generation.

The first reviewed benchmark found Hybrid stronger on retrieval coverage, correctness,
groundedness and relevance, while gold-citation recall remained approximately 0.43 in both
modes. See [Evaluation results](../operations/evaluation-results.md). The next milestone is
therefore adaptive evidence acquisition through a bounded Agentic RAG mode. Knowledge-graph
retrieval follows as an additional evidence tool for the same orchestration layer.

## Design rules

1. Keep Vanilla and Hybrid behaviour unchanged as experimental controls.
2. Put retrieval capabilities behind typed, directly testable, read-only tools before adding
   an LLM planner.
3. PostgreSQL remains authoritative for paper/build identity and metadata; Qdrant remains
   authoritative for searchable chunk vectors. Tools may combine them but must respect
   SQL-active or evaluation-frozen build IDs.
4. Every returned fact must retain paper, build, chunk, page and section provenance.
5. Bound agent iterations, retrieved context, tokens and wall time. A default maximum of
   three retrieval rounds is the starting policy.
6. Trace plans, tool calls, retrieved evidence, model use, latency and failures in Langfuse.
7. Do not perform paid model calls in automated unit tests.
8. Do not introduce graph infrastructure during the Agentic milestone merely to anticipate
   KG-RAG; add it only after the agentic baseline is measurable.

## Phase 1 — shared retrieval foundation

Implementation status:

- complete: shared `RetrievalScope`, `PaperMatch` and `EvidenceChunk` contracts;
- complete: PostgreSQL `search_papers` and scoped Qdrant `search_chunks`;
- complete: separate Vanilla/Hybrid mode modules using the shared scope boundary.

Implement framework-independent functions with typed inputs and outputs:

| Tool | Store | Purpose |
| --- | --- | --- |
| `search_papers` | PostgreSQL | Resolve papers/builds by title, author, year, source and metadata terms |
| `search_chunks` | Qdrant | Run dense or Hybrid search within explicit build/paper filters |

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

Implementation status: complete as read-only tools; they are not yet exposed to an agent.

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
- current Vanilla/Hybrid pipelines can use the shared primitives without metric drift;
- each tool has a Langfuse span and returns complete evidence provenance.

## Phase 4 — agent planning contracts

Implementation status: complete as data contracts; no planner model or Agentic runtime is
enabled yet.

`src/api/rag/modes/agentic/contracts.py` defines strict Pydantic contracts for:

- question scope, explicit evidence needs and an auditable plan summary;
- discriminated actions for only `search_papers`, `search_chunks`, `get_section` and
  `get_neighbors`;
- per-need evidence sufficiency and `synthesize`, `continue` or `abstain` decisions;
- deterministic stop reasons and application-owned limits for rounds, tool calls, evidence,
  elapsed time and planner tokens;
- action fingerprints so the Phase 5 executor can detect repeated searches independently
  of planner-generated action IDs.

Unknown fields, unknown tools, dangling need references and contradictory sufficiency
decisions fail validation. The schemas contain concise, auditable summaries rather than
private chain-of-thought, executable code or unconstrained free-form actions. No ingestion,
deletion or database-mutation action belongs in these contracts.

Exit criteria are satisfied by offline tests covering strict provider schemas, action and
reference validation, sufficiency invariants, duplicate-action fingerprints and deterministic
budget exhaustion. Phase 5 must use these contracts at every model/executor boundary rather
than duplicating them in prompts or framework-specific state.

## Phase 5 — bounded Agentic RAG mode

Implementation status: complete as the API/runtime milestone. Streamlit exposure was added in
Phase 6; benchmark exposure remains Phase 7 work.

The explicit `agentic` mode now uses a structured planner/executor/shared-synthesizer loop:

1. Classify whether the question needs one paper, multiple papers or metadata discovery.
2. Decompose multi-part and comparison questions into evidence needs.
3. Select tools and explicit paper/build filters.
4. Assess evidence sufficiency after each retrieval round.
5. Reformulate or narrow an unsuccessful search when useful.
6. Generate the final answer only from accumulated evidence, with chunk-level citations.

The loop must terminate after at most three retrieval rounds by default. It must also stop
when evidence is sufficient, the budget is exhausted, or repeated searches add no new
evidence. Insufficient evidence must produce an explicit abstention rather than an invented
answer. The agent receives read-only corpus tools; ingestion, deletion and database mutation
are outside its authority.

This is intentionally a constrained retrieval agent. Merely asking an LLM to choose between
the existing Vanilla and Hybrid functions, without decomposition, evidence checking or
iterative retrieval, does not satisfy this milestone.

Implemented safeguards and exit criteria:

- `POST /rag2` accepts `mode: "agentic"` and returns the selected mode, corpus fingerprint,
  ordinary verified citations and concise `execution` metadata;
- the executor intersects every action filter with the immutable active/frozen corpus scope;
- at most three rounds run by default, with independent tool-call, evidence, elapsed-time and
  planner-token limits;
- repeated actions, repeated evidence, two empty-result rounds, tool failures, planner/schema
  failures and explicit insufficiency all terminate without ungrounded generation;
- direct questions can synthesize after one search and one sufficiency decision;
- offline tests cover termination, scope escape, invented evidence IDs, repeated actions and
  results, tool failure, abstention and strict provider requests.

The implementation is isolated in `src/api/rag/modes/agentic/`: `contracts.py` defines the
boundary, `planner.py` owns structured model calls, and `executor.py` owns deterministic tool
execution. The existing answer generator is the synthesizer and still enforces retrieved
chunk IDs, so Agentic citations follow the same contract as Vanilla and Hybrid.

## Phase 6 — API, Streamlit and observability

Implementation status: complete.

Streamlit exposes **Agentic** alongside **Vanilla** and **Hybrid**. The existing comparison
key isolates chat state by corpus, mode and answer model while preserving the corpus
fingerprint across mode switches for fair comparisons. Each Agentic answer has a collapsed
execution panel containing only the validated plan summary, outcome, rounds, successful tool
counts, papers touched, evidence count and elapsed time. It does not expose prompts, evidence
text or hidden reasoning. Existing source and figure rendering still uses verified citation
IDs.

Langfuse receives the complete safe execution hierarchy: `rag_request` → `rag_pipeline` →
`agentic_retrieval`, with child planner/sufficiency generations, read-only tool spans and the
shared final generation. Validated actions/filters, evidence IDs, budget usage, stop reason,
model usage and latency are attached to their relevant spans. Tracing remains optional and
cannot change request behaviour. Omitted/legacy requests are not routed through the agent.

## Phase 7 — evaluation

Add `agentic` to `evals/run_benchmark.py` using the same reviewed questions, frozen builds,
answer model and top-k/context policy wherever comparable. Record each mode as a separate
Langfuse Dataset Experiment.

Add agent-specific measures:

- retrieval/tool rounds and duplicate-search rate;
- evidence coverage and citation recall;
- successful decomposition for cross-paper questions;
- correct abstention when evidence remains insufficient;
- latency, token usage and estimated model cost.

Run a small smoke evaluation first, followed by the full development set. Do not declare an
improvement from judge scores alone; inspect per-question regressions and retrieved evidence.

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
4. structured planning contracts (complete);
5. bounded planner/executor with an API-only `agentic` mode (complete);
6. Streamlit mode and Langfuse trace presentation (complete);
7. benchmark integration and evaluation-set strengthening;
8. graph schema/provenance, deterministic KG retrieval, then KG-Agentic composition.

Do not start a later slice while an earlier slice lacks offline tests, provenance guarantees
or evaluation compatibility.
