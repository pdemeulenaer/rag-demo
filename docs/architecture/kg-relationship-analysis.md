# KG relationships: current capability and next implementation

## Status — 2026-10-30

**This page specifies planned work, not an implemented analysis command.** Existing KG
extraction, review, publication and deterministic retrieval remain available. Retain query
policy `hybrid-reviewed-graph-v5`; do not change retrieval, merge scientific identities,
approve candidates or run paid extraction merely to follow this plan.

The immediate milestone is to inspect the extraction already available and find a useful
connected subset. Completing all papers/chunks is **not** a prerequisite for that analysis.
Unrelated papers may remain disconnected; never invent links to make a larger component.

## Three capabilities that must not be confused

| Capability | Meaning | Current status |
| --- | --- | --- |
| Graph-assisted passage retrieval | Use reviewed entities/assertions and their source links to find useful original text chunks | Implemented in `kg`; the narrow pilot demonstrates examples of benefit |
| Multi-hop scientific evidence retrieval | Join several relevant scientific assertions through justified entity identities and retrieve evidence for each link | Not demonstrated as a general capability; needs the analysis and retrieval work below |
| Scientific synthesis/reasoning | Interpret the connected evidence while preserving conditions, uncertainty, hypotheses and disagreements | LLM generation is present, but graph paths and model explanations are not scientific proof |

Here a **passage** usually means an existing full-text chunk, not a newly generated summary.
Current KG mode runs Hybrid, expands through bounded reviewed graph records, protects strong
Hybrid evidence and sends selected **original chunks** to the shared answer generator. It
does not give the generator an independently verified graph-derived conclusion.

An improvement such as retrieving the missing classifier-results passage is a legitimate
retrieval benefit. It does not, by itself, demonstrate relationship-dependent reasoning.

### Structural edges versus scientific steps

The reader traverses `HAS_OBSERVATION`, `SUBJECT` and `OBJECT` structural links, at most two
per path. For example, `entity → relationship assertion → entity` has two database edges
but represents **one** scientific relationship. `SUPPORTED_BY`, publication membership,
build and source links establish provenance, not additional scientific reasoning steps.
Publication also stores predicate edges; their existence does not mean the current reader
plans predicate-specific scientific chains. General entity resolution and KG-Agentic are
not implemented.

The existing read-time object resolver conservatively groups source-supported M/NGC/IC
identifiers. It is not permission to equate generic populations, datasets or methods. Two
populations labelled "2P" or "Al-rich" need not identify the same population, even within
studies of the same cluster. Preserve their definitions, samples and source attribution.

### Example of a relationship-dependent question

Hypothetically, Paper A identifies Population P in Cluster X as aluminium-rich, Paper B
reports radial anisotropy for that **same justified population**, and Paper C identifies
the observational dataset supporting the measurement. A question asking which enriched
populations exhibit anisotropy and which observations support it requires joining those
assertions; the intermediate population/measurement may not be named in the question.

That chain does **not** establish that enrichment caused anisotropy. Observations,
assumptions, simulation results, proposed origins and future work remain different kinds
of evidence. A cross-paper comparison of unrelated measurements, or a question explicitly
naming two papers, need not require a scientific graph join at all.

## Planned implementation slices

Implement and test one slice at a time. Use existing typed extraction/source contracts,
validation and identity utilities; an offline index/adjacency map does not need a new agent
framework. No code or command described as planned below is available merely because it
appears on this page.

### 1. Offline coverage and relationship audit — first implementation

Read a coherent, fingerprinted snapshot of the selected directory's `plan.json`,
`checkpoints.sqlite`, saved extraction batches/quarantine and optional review decisions.
Use the authoritative typed batches, not just serialized display-graph edges. Coordinate
with the existing directory-lock/snapshot mechanism; if extraction changes inputs during
analysis, fail/retry explicitly rather than mix generations. Do not modify checkpoints,
reviews or the active publication. A long-running extraction must not be interrupted.

Automate these outputs:

- Per-paper/build planned chunks, completed/failed/pending chunks, and completion fraction.
  Prepared inputs, attempted chunks and successfully extracted chunks are different counts.
- Counts of entities by kind, observations by kind, and scientific relationships by predicate.
  Report provenance/structural edges separately, never as scientific relationship totals.
- Distinct source chunks supporting records, duplicates/overlap and records lacking valid
  endpoints or provenance. Successful extraction is not exhaustive semantic coverage.
- Separate **unreviewed**, **approved and dependency-eligible**, **excluded** and
  **quarantined** counts/projections. Without a matching review, approved coverage is unknown
  or zero, not an assumption that all candidates are usable. Stale review fingerprints must
  be flagged, never silently applied to changed candidates.
- Candidate relationship opportunities versus currently supported/approved ones. A large
  number of entities or observations alone does not establish useful connectivity.

Save a new local machine-readable report plus a short Markdown summary, with plan ID,
candidate/review fingerprints, audit version, input scope and truncation flags. The initial
audit must be configuration-free: no `.env` reads, network/model calls, Neo4j writes or
scientific approvals. Local provenance validation cannot certify current PostgreSQL
eligibility; publication/runtime must still perform their existing scope checks.

Suggested future command name: `make kg-analyze KG_DIR=...` — **planned, not runnable yet**.

### 2. Conservative cross-paper identity proposals

Build indexes by entity kind and literal source-supported identifier, using the existing
catalogue normalization rules where applicable. Reuse approved alias evidence rather than
creating an all-pairs name-similarity search. Produce a proposal sidecar containing the
original record/build IDs, names, quotes, matching basis and conflicts.

Keep three explicit categories: justified identity within the existing reviewed rules,
possible identity requiring review, and conflicting identity held apart. Candidate-only
inputs remain provisional even if identifiers match. Broader synonyms, method/dataset
equivalence and population identity require explicit evidence/review; text similarity can
suggest candidates but cannot authorize a merge. Never globally merge measurements or
overwrite disagreements. A review decision must be versioned and source-bound; applying
new identity types to publication/runtime is a later tested change, not an audit side effect.

### 3. Bounded scientific evidence-chain discovery

Construct an **analysis-only** projection over typed observations and relationships plus
justified identity links. Inspect small connected components and bounded path/join templates,
for example:

- the same astronomical object with distinct attributed findings in different papers;
- an observation linked by `uses_dataset` or `observed_with` to its measurement context;
- a population `located_in` an object with source-backed findings, subject to justified
  population identity;
- separately labelled origin/enrichment hypotheses and the observations they discuss.

The first example is useful cross-paper aggregation, not automatically a multi-hop result.
Emit candidate chains with each typed assertion, direction, subject/object, epistemic
status, conditions, supporting quotes, paper/build/chunk IDs and identity justification.
Count scientific assertions separately from storage edges and identity bridges. Distinguish
within-paper from cross-paper chains, and candidate-only from fully approved paths.

Use explicit maximum path length, component work, high-degree expansion and output caps;
sort deterministically and report truncation. Avoid unrestricted path enumeration, cycles,
provenance-only connections, generic-label joins and treating many overlapping chunks as
independent corroboration. Shared subjects do not establish causation. Unit compatibility
or similar numeric values do not establish that two measurements share conditions.

### 4. Focused review and optional paid assistance

Rank a small review queue by cross-paper reach, useful predicate diversity, evidence
availability and missing identity/relationship dependencies. These are navigation heuristics,
not scientific confidence scores. Let the reviewer inspect each complete source-backed chain
and approve/exclude its underlying records and any new identity decision through explicit,
versioned review mechanisms. Analysis itself must never bulk-approve.

If the audit finds a missing link, first inspect existing source context. An optional LLM
may propose a typed relationship/identity from bounded cited excerpts; this must be a separate
explicitly paid, checkpointed action with call/token limits. Keep proposals local, validate
quotes/endpoints/roles and require review before publication. Verbatim quotes establish
literal provenance, not that the interpretation is correct. Any required schema extension
needs a versioned design; do not invent unsupported predicates to fit a desired answer.

### 5. Demonstrate the connection before extending runtime

Select a connected, sufficiently reviewed subset based on the audit, not on answers to
existing benchmark questions. Author independently reviewed questions requiring an identifiable
join; include simple controls and missing-link/ambiguous-identity cases. Freeze sources and
review decisions before testing. Path suggestions can help write development questions, but
a graph-derived question set is not an unbiased held-out comparison.

For every proposed multi-hop item, record the required scientific assertions, their sources,
the intermediate identities and why one passage does not already supply the entire answer.
The `cross_multihop` dataset profile alone is not proof of graph traversal or necessity.

Then implement a bounded, typed, read-only path-retrieval capability using the approved
projection. It must return original source evidence for every necessary link and a compact
path witness, preserve active/frozen scope, and expose actual path use separately from graph
passage additions. Do not merely increase `*0..2` or raise top-k/token budgets and call it
reasoning. Decide whether/how to expose it in deterministic KG before optional `kg_agentic`
composition; preserve existing mode controls.

Compare Hybrid and KG using identical corpus scope, models and documented context/search
budgets. Include an ablation with relationship traversal disabled but the other selection
behaviour retained where feasible. Report correctness, factual/relationship support,
identity mistakes, missing-link abstentions, actual new evidence, latency and extraction/
review cost. Do not credit gains from extra context or generation variability solely to graph
structure. Every semantic assessment remains fallible. Paid runs remain explicit user work.

## Exit criterion for the first slice

A reproducible local audit should tell us **which papers actually have extracted evidence,
which scientific predicates exist, which cross-paper identities are justified, and which
small chains are worth reviewing**. An honest report of insufficient connectivity is useful:
it directs targeted extraction/review instead of requiring another full-corpus paid run.

See [KG construction and publication](knowledge-graph.md), [current roadmap](rag-evolution-roadmap.md#current-next-steps-2026-10-30)
and [evaluation results](../operations/evaluation-results.md).
