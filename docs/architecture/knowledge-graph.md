# Knowledge-graph RAG

## Status and decisions

**Phases 8.1–8.2 — foundation and offline extraction are implemented.** There is an optional Neo4j Community
container, an explicit seven-paper selection, an offline preview and typed scientific
extraction records with source-identity/quote validation, a full-artifact loader and bounded,
checkpointed paid extraction. No graph writer, activation, graph retrieval,
`kg`/`kg_agentic` API mode or UI option exists yet. Extraction saves local review candidates,
not query-ready facts. Implementation tests do not make paid requests.

The target is all eligible papers, not a permanent seven-paper corpus. Validate the
connected pilot first, then expand. Unrelated papers may form disconnected components;
never manufacture a relationship just to connect the graph.

## Storage responsibilities

| Component | Authority |
| --- | --- |
| PostgreSQL | Paper identity, active builds and ingestion lifecycle |
| Qdrant | Existing dense/BM25 vectors and chunk retrieval |
| Neo4j | Derived scientific entities, attributed observations and source-backed relationships |
| Application | Corpus scope, mode selection, generation, citation validation and Langfuse |

Neo4j is an additional derived index, not a replacement catalogue or vector database.
Store references to existing paper/build/collection/point IDs; do not invent a second
authoritative document identity. Paper and Chunk graph nodes will represent those existing
identities, not new documents or a second chunking pipeline.

### Role of `neo4j-graphrag`

The optional `kg` dependency group pins `neo4j-graphrag[openai]==1.22.0`. Its
[KG builder](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html)
is currently experimental and allows individual/customized components.
`src/api/kg/extraction.py` implements a supported custom `Component`, returning validated
scientific records and the library's `Neo4jGraph` staging representation. It uses the shared
native OpenAI SDK/Pydantic parser with a closed scientific schema. We deliberately do not
use the default `LLMEntityRelationExtractor` provider schema: its generic graph properties
are open-ended dictionaries, unlike our strict typed scientific records. No manual schema
rewriting or JSON repair is performed. This is not adoption of the entire default builder.

Reuse full page-aware Markdown chunks from verified build artifacts. Do not run the
package's default PDF loader/splitter, assign replacement chunk IDs, or regenerate vectors.
Its [Qdrant retriever](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html#qdrant-retrievers)
can map external hits to graph nodes. Its built-in Hybrid retriever, however, uses Neo4j
vector/full-text indexes: it is not our Qdrant dense + BM25 + RRF pipeline. Preserve that
existing pipeline and add bounded graph expansion from its result IDs where appropriate.
Keep the existing generator and citation checks, rather than replacing the application
with the package's complete answer pipeline.

## Scientific schema v1

`src/api/kg/contracts.py` defines `scientific-kg-v1`:

- **Entity:** astronomical object, method, dataset, instrument or author, with source
  evidence. Alias strings are candidates, not permission to merge objects globally.
- **Observation:** measurement, upper/lower limit, simulation result or hypothesis.
  Record the subject, statement, literal value, units, uncertainty and conditions.
- **Relationship:** uses a method/dataset, observed with an instrument, located in,
  compared with, or proposed origin. Proposed origins must remain hypotheses.
- **EvidenceReference:** paper, build, collection, point, source, page, section and
  a literal supporting quote. Every entity/observation/relationship needs evidence.
- **ExtractionBatch:** one source build plus extraction model and revision. Record IDs
  are build-local; the writer must namespace them by build/extraction revision.

Different papers or conditions produce separate observations. Never overwrite a measurement
with another paper's value, flatten uncertainties, or promote a proposed explanation into
an established fact. Preserve ambiguous/damaged numerical passages for review; do not guess
missing signs, exponents or digits. The initial model is `gpt-5-mini`, with `low` reasoning
and a 16,384-token completion cap (reasoning plus output), configurable before preparation.

`validate_sources()` rejects unknown point IDs, wrong source metadata and quotes absent
from supplied full chunks. It proves literal provenance only, **not scientific entailment**.
The full-artifact loader verifies hashes and exact evaluation-frozen, ready PostgreSQL
build scope, including retained ready builds; deleted papers are rejected. Source checks
alone do not make a batch query-ready. The writer/resolver still
needs schema-semantic validation, alias review and staged activation tests.

## Initial paper selection

`src/api/kg/pilot.json` fixes paper IDs, titles and group labels from the saved v4 corpus:

| Group | Paper |
| --- | --- |
| M22 | A Homogenized Catalogue of Variable Stars in the Globular Cluster M22: Membership, Physical Parameters, and Distance |
| M22 | Tracing M22's origins: Spatial and chemical constraints on its formation history |
| ω Centauri | The chemo-dynamical complexity of ω Centauri: different kinematics for different populations |
| ω Centauri | Bar-induced migration of $ω$ Centauri away from Gaia Sausage-Enceladus |
| 47 Tucanae | Axion Constraints from White Dwarf Cooling in 47 Tucanae |
| 47 Tucanae | Unresolved Binary Systems in the Rubin Era I: An Autoencoder Framework for Binary Identification Applied to 47 Tucanae |
| Connecting survey | Globular Clusters in the Time of the JWST. I. Survey Design and First Results on Multiple Populations and Beyond |

The survey includes NGC 6656/M22 and NGC 104/47 Tuc; the M22 formation paper compares its
findings with ω Centauri. These are selection reasons from saved abstracts, not already
extracted/validated graph edges. Verify actual full passages before writing relationships.

Later add the connected Little Red Dot group: *From Feedback-Free Star Clusters to Little
Red Dots via Compaction*, *SPURS: An Ultra-deep View Inside the Compact, Nitrogen-Enriched
Nuclei of Little Red Dots*, and *The Ashes of Supermassive Stars: Globular Cluster-like
Aluminum Enhancement in Little Red Dots*. Then process all eligible builds.

## Commands now

```bash
make kg-preview           # Seven papers in the saved v4 snapshot
make kg-schema            # Inspect the Pydantic-generated extraction JSON schema
make kg-up                # Start Neo4j and wait for health
make kg-status
```

Browser: **http://localhost:7474**. Username: `neo4j`. The local-only initial password is
`neo4j-local-only`, unless `NEO4J_PASSWORD` in your environment/`.env` overrides it. Merge
the setting into your existing `.env`; do not overwrite that file with `.env.sample`.
Changing the variable does not change the password of an already initialized database.

The container is pinned to `neo4j:2026.09.0`, binds browser/Bolt ports to localhost, and
uses persistent `neo4j_data`/`neo4j_logs` volumes. `make kg-stop` stops it without deleting
data. `make kg-logs` follows logs. Normal `make compose` does not start Neo4j. The service
shares the repo's default Compose network but has no dependency on the API or ingestion.
This is local development infrastructure, not a secured production deployment or backup
policy. See [Neo4j Docker guidance](https://neo4j.com/docs/operations-manual/current/docker/introduction/).

Preview every paper in that snapshot, or provide another saved corpus/pilot:

```bash
make kg-preview KG_SELECTION=all
make kg-preview KG_SNAPSHOT=path/to/snapshot.json KG_PILOT=path/to/pilot.json
```

Preview only reads `papers`, frozen build IDs and corpus identity from local files. It
does not load `.env`, connect to services, read reference answers, generate embeddings,
invoke a model, or write files/databases. Repeating it produces the same plan for the
same inputs. Missing pilot papers fail rather than silently shrinking the selection.
`all` means **all papers in the specified snapshot**, not today's live database.
`graph_ready: false` is intentional: the preview has not verified full artifacts or built
a graph. The snapshot's sampled evaluation excerpts are not the extraction input.

## Extract and review the pilot

No Neo4j service or API rebuild is needed for this step. PostgreSQL and the existing full
paper artifacts must be accessible. Preparation reads catalogue state but changes no
PostgreSQL/Qdrant data. It verifies the saved manifest against PostgreSQL, byte lengths
and SHA-256 hashes of `chunks.json`, `pages.json` and `document.md`, contiguous chunk order
and stable point identities. Uploads additionally verify `payloads.json` text IDs/content.
It does not re-download PDFs, re-embed text, audit live Qdrant vectors or read gold answers.
For local storage, Docker artifact paths map to `PAPERS_ARTIFACT_DIR`; Azure reads are confined
to the configured private paper-artifact container, not arbitrary URLs. Figure storage
`STORAGE_MODE` is unrelated to `PAPERS_STORAGE_MODE`.

Start with the first pilot paper and five chunks:

```bash
# Free: freeze one paper's complete existing text chunks and extraction configuration.
make kg-prepare KG_DIR=data/knowledge_graph/smoke-v1 KG_PAPERS=1

# PAID: at most five chunk requests, with default parallelism 2.
make kg-extract KG_DIR=data/knowledge_graph/smoke-v1 KG_MAX_CALLS=5

# Free: validate saved records, links, quotes and staging graph consistency.
make kg-validate KG_DIR=data/knowledge_graph/smoke-v1
```

Open `data/knowledge_graph/smoke-v1/candidates.json`. Compare each record's quote against
the full chunk in `plan.json`, including its page and section. Check that the quote actually
supports the statement, subject, value, units, conditions and epistemic status. Empty
results are valid for boilerplate chunks. Local validation cannot assess scientific truth
or approve alias merges. `review_status: needs_review` and `graph_ready: false` remain
intentional; no approval/publishing command exists in this slice.

Five chunks are a wiring/quality smoke test, **not a complete paper graph**. Repeat the same
`kg-extract` command to process the next pending chunks, then validate again. Preparation
reports the full first-pass call count: a long paper can have many more than five chunks.

After reviewing the smoke test, prepare all seven papers in a separate directory:

```bash
make kg-prepare KG_DIR=data/knowledge_graph/pilot-v1
make kg-extract KG_DIR=data/knowledge_graph/pilot-v1 KG_MAX_CALLS=10
make kg-validate KG_DIR=data/knowledge_graph/pilot-v1
```

Each directory is a separate extraction run: the complete pilot will independently process
the smoke paper again. Successes are skipped **within the same directory**, not across
directories. If you want to avoid that duplicate cost, start with all seven prepared in
`pilot-v1`, use `KG_MAX_CALLS=5`, review, and keep resuming that directory instead.

### Sample across papers instead of finishing one paper first

Use the **existing** prepared directory; no new preparation or model setting is needed:

```bash
# PAID: up to three distinct attempted chunks per paper, across all seven papers.
make kg-extract KG_CHUNKS_PER_PAPER=3 KG_MAX_CALLS=21
make kg-validate
```

The selector prefers substantial body sections and distributes chunks through each paper,
then interleaves papers round-robin. These are structural heuristics, not scientific review;
if insufficient body chunks exist, it falls back to other available chunks. The least-sampled
papers go first when the global cap is smaller than the number of papers. The summary lists
`papers_selected_this_invocation` with titles and request counts.

`KG_CHUNKS_PER_PAPER` is a **directory-lifetime quota on distinct attempted chunks**, not a
fresh per-invocation allowance. Existing successful, failed and interrupted attempts count.
If the first paper already has 15 attempted chunks, a quota of 3 skips that paper and samples
up to 3 from each of the other six (18 requests maximum). Repeating the same sampling command
only fills outstanding quotas; completed samples are not charged again. Sampling failures
still consume a slot. To sample more, explicitly increase the quota; to resume normal full
extraction, omit `KG_CHUNKS_PER_PAPER`. Sampling does not shrink/change the frozen plan, and
does not permit automatic retries. Allowed quota: 1–1000; the global `KG_MAX_CALLS` still applies.
This is a CLI/Make option, not a model setting to put in `.env`.

### Understand and retry rejections

New application rejections save specific `safe_diagnostics.rejection_issues` in
`checkpoints.sqlite` and `failures.json`, print their code/path in the terminal, and attach
them to optional Langfuse generation metadata. Examples:

- `quote_not_found at observations.2.evidence.0.quote`: the quotation is not an exact substring
  of the source chunk.
- `duplicate_record_id at observations.0.id`: an ID was already used in this chunk.
- `undeclared_observation_subject`: an observation names an entity not declared in the output.
- `undeclared_relationship_endpoint`: a relationship references a missing entity/observation.

Paths use **zero-based** list indices. SDK schema/truncation/refusal diagnostics remain separate.
Record text, quotation contents, raw validation inputs and exception messages are not saved
in rejection logs; token usage and provider model/response ID are retained when available.
Every retry remains a paid, explicit request; the validation checks are unchanged.

For an unambiguous failed/interrupted-only retry, without processing new pending chunks:

```bash
make kg-extract KG_FAILED_ONLY=true KG_MAX_CALLS=4
make kg-validate
```

Do not combine sampling with retry options. Existing `KG_RETRY_FAILED=true` retains its older
behavior: it includes **both pending and failed/interrupted** chunks. `KG_FAILED_ONLY=true`
excludes pending chunks. Both skip completed chunks. All attempt history stays in SQLite,
while `failures.json` shows the current unresolved failures. Old failures that only saved
`ExtractionRejected` cannot be diagnosed retroactively; they are marked `reason_not_recorded`
until an explicit new attempt records a specific reason or succeeds.

### Checkpoint storage and budgets

- `plan.json` freezes the full text, exact build identities, manifest hashes, schema/prompt
  revision, package version and model settings. Repeating identical preparation is safe;
  different scope/settings cannot overwrite it. Use a new `KG_DIR` when changing these.
- `checkpoints.sqlite` records each reserved attempt, result, tokens when known, failure
  category and latency. A per-directory lock prevents concurrent writers. Completed chunks
  are reused. Failed/interrupted chunks are skipped by default; successful siblings survive.
- No SDK or schema retries happen implicitly. To explicitly retry failures/unknown outcomes:
  `make kg-extract KG_DIR=... KG_MAX_CALLS=5 KG_RETRY_FAILED=true`.
  A retry may be billed again. A crashed request may have been billed without a saved result;
  exact-once provider billing is not guaranteed. Missing usage is labelled unknown, not zero.
- `KG_MAX_CALLS` limits requests **per invocation**, including explicit retries; repeating
  the command incurs additional costs. It is not a lifetime token/dollar budget.
- Extraction can continue from its frozen local plan without PostgreSQL. This does not
  certify that those builds are still active; the future publisher/retriever must recheck
  PostgreSQL scope before exposing observations. It must not activate a graph solely from
  this offline plan or validation result.

| Setting | Default | Enforced range / meaning |
| --- | --- | --- |
| `KG_MODEL` | `gpt-5-mini` | Model must support native structured output and the reasoning parameter |
| `KG_REASONING_EFFORT` | `low` | Provider-supported effort; frozen at preparation |
| `KG_MAX_COMPLETION_TOKENS` | 16384 | 1024–32768; reasoning + structured output per call |
| `KG_TIMEOUT_SECONDS` | 180 | 10–600 seconds per SDK request |
| `KG_MAX_CALLS` | 10 | 1–1000 requests per invocation; Make override is optional |
| `KG_CONCURRENCY` | 2 | 1–8 independent chunk requests in parallel |

The provider schema additionally bounds each chunk to 40 entities, 80 observations,
80 relationships and five quotes per record. These are conservative pilot extraction bounds,
not limits on the stored source text. Records need exact quotes and valid declared endpoints;
separate conflicting assertions are not automatically deduplicated or globally merged.

If `LANGFUSE_ENABLED=true`, the existing `LANGFUSE_*` settings are reused for `kg.extract`
generation observations with source text, build/point/plan identity, model/revision, usage
and latency. Tracing is optional and best-effort; local checkpoints are authoritative.
No LangSmith is used. Source text is sent to the configured model and, when enabled,
Langfuse; keep the local extraction directory private and backed up.

`make kg-test` exercises the actual GraphRAG component and native SDK parser using mocked
HTTP responses, plus hash/scope validation, refusal/failure handling and resumption.
It makes no paid requests and writes no external databases. Normal `make test` skips
optional extraction tests if the `kg` group is absent.

See [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
for native typed parsing. Schema conformance is not a substitute for scientific review.

## Remaining implementation slices

1. **Offline extraction (implemented):** verified full artifacts, typed library component,
   explicit paid command, bounded parallelism, local checkpoints and optional Langfuse.
   Run a small paid pilot and scientifically review candidates before graph persistence.
   No daily automation yet.
2. **Graph persistence:** constraints and build-local idempotent writes, conservative alias
   resolution, staged graph-build activation. Failed replacements retain the old graph;
   stale observations cannot leak through a shared entity. PostgreSQL remains authoritative.
3. **Deterministic KG mode:** bounded, parameterized read-only graph queries return original
   supporting chunks under the same scope. Add a separate mode module, API, UI and runner.
   Start without unrestricted LLM-generated Cypher.
4. **KG-Agentic:** add the tested graph tool to existing LangGraph orchestration without
   changing the four existing modes; record paths, supporting IDs and stage latency.
5. **Comparison and daily integration:** reuse reviewed questions, add genuinely relational
   human-reviewed questions, pin graph extraction/build identity in frozen evaluations and
   compare identical paper scopes. Integrate incremental extraction only after validation.

During the pilot, do not compare a seven-paper graph against unrestricted 48-paper retrieval
as if their coverage were equal. Graph incompleteness is not evidence that a fact is absent.
No vector re-indexing or wholesale evaluation regeneration is inherently required; existing
point IDs and approvals remain untouched. No KG quality/latency improvement is claimed yet.
