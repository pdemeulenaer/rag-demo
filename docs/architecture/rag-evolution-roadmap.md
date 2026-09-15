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

## Phase 1 — reusable retrieval tools

Implement framework-independent functions with typed inputs and outputs:

| Tool | Store | Purpose |
| --- | --- | --- |
| `search_papers` | PostgreSQL | Resolve papers/builds by title, author, year, source and metadata terms |
| `search_chunks` | Qdrant | Run dense or Hybrid search within explicit build/paper filters |
| `get_section` | Artifacts/Qdrant | Retrieve additional evidence from a named paper and section |
| `get_neighbors` | Artifacts/Qdrant | Expand around a promising chunk without issuing another broad search |

Tool results must use a shared evidence model and must not return unregistered or inactive
builds. For frozen evaluations, they must be constrained to the snapshot's build IDs.

Neighbour retrieval requires a stable `chunk_index` (or equivalent ordinal) persisted in
the chunk artifact, manifest and Qdrant payload. Adding it may require an extraction pipeline
version bump and explicit reindexing; never infer ordering from UUIDs.

Exit criteria:

- deterministic offline unit tests cover filters, empty results, invalid identities and
  scope enforcement;
- current Vanilla/Hybrid pipelines can use the shared primitives without metric drift;
- each tool has a Langfuse span and returns complete evidence provenance.

## Phase 2 — bounded Agentic RAG mode

Add an explicit `agentic` mode with a structured planner/executor/synthesizer loop:

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

Exit criteria:

- API response records the selected mode, plan summary, citations and corpus fingerprint;
- unit tests cover termination, repeated-result detection, tool failures and abstention;
- latency, tool rounds and token use are observable and bounded;
- direct single-paper questions do not incur unnecessary retrieval loops.

## Phase 3 — UI integration

Expose **Agentic** alongside **Vanilla** and **Hybrid** in Streamlit. Keep chat state isolated
by corpus and mode. Show concise execution metadata—such as papers searched and retrieval
round count—without exposing hidden reasoning or raw prompts. Existing source and figure
rendering must continue to use verified citation IDs.

## Phase 4 — evaluation and Langfuse

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

## Phase 5 — strengthen the evaluation set

Before tuning or presenting final comparisons:

- add more genuinely multi-paper questions;
- approve corpus-level unanswerable questions that test abstention;
- include several human-written research questions to reduce synthetic bias;
- create development and held-out splits at paper/group level to prevent leakage;
- repeat final runs or bootstrap item-level differences to quantify uncertainty.

Use the development split while implementing. Reserve the held-out split for milestone
comparisons.

## Phase 6 — knowledge-graph RAG

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

1. shared evidence model and `search_papers`;
2. scoped `search_chunks`;
3. stable chunk ordinals plus section/neighbour expansion;
4. bounded planner/executor with an API-only `agentic` mode;
5. Streamlit mode and Langfuse trace presentation;
6. benchmark integration and evaluation-set strengthening;
7. graph schema/provenance prototype;
8. deterministic KG retrieval, then KG-Agentic composition.

Do not start a later slice while an earlier slice lacks offline tests, provenance guarantees
or evaluation compatibility.
