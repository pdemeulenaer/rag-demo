# Knowledge-graph RAG

## Status and decisions

**Foundation, offline extraction/review and staged Neo4j publication are implemented.** There is an optional Neo4j Community
container, an explicit seven-paper selection, an offline preview and typed scientific
extraction records with source-identity/quote validation, a full-artifact loader and bounded,
checkpointed paid extraction, approved-only immutable publication, content verification
and explicit activation. Deterministic `kg` retrieval, API/Streamlit selection and benchmark
support are implemented; `kg_agentic` remains planned. Extraction alone saves local review
candidates, not published facts.
Implementation tests do not make paid requests.

The target is all eligible papers, not a permanent seven-paper corpus. Validate the
connected pilot first, then expand. Unrelated papers may form disconnected components;
never manufacture a relationship just to connect the graph.

## How papers reach Neo4j

KG construction is a **second, derived indexing pipeline**, using papers already ingested
into PostgreSQL/Qdrant. It does not replace ordinary paper ingestion:

```text
Existing PDF → page-aware Markdown chunks → PostgreSQL catalogue + Qdrant vectors
                                            ↓
                       kg-prepare → kg-extract → validate + scientific review
                                            ↓
                     Neo4j publication/activation → KG retrieval → cited answer
                         (implemented)               (implemented)
```

### Step-by-step: from existing chunks to an active graph

**Prerequisite:** ingest the PDFs normally first. PostgreSQL must contain ready paper builds,
and their full Markdown/chunk artifacts and Qdrant points must already exist. The steps
below reuse those chunks; they do not reprocess PDFs or create new embeddings.

All seven steps are implemented. Local files are written under the chosen `KG_DIR`;
only staging and activation write to Neo4j.

| Step | Command | Plain-language meaning | Result |
| --- | --- | --- | --- |
| **1. Freeze selected chunks** | [`make kg-prepare`](#first-run-or-fresh-extraction-pilot) | Verify the selected paper builds and artifact hashes, then save their existing full chunks, identities and extraction settings as a fixed local input set. **This does not freeze or lock your databases.** | `plan.json`: repeatable inputs for this extraction run. Changing the inputs/settings requires a new directory. |
| **2. Extract candidates** | [`make kg-extract`](#first-run-or-fresh-extraction-pilot) | Ask the LLM to identify entities, measurements and relationships, with references to exact source passages. **Paid; local outputs only, no Neo4j writes.** | `checkpoints.sqlite` and `candidates.json`; records are candidates, not approved facts. |
| **3. Validate automatically** | [`make kg-validate`](#understand-and-retry-rejections) | Check structure, identifiers, dependencies, scientific role rules and exact supporting quotations. **Passing does not establish scientific correctness.** | A validation report, including completeness and quarantined-record counts. No approvals or activation. |
| **4. Review and approve** | [`make kg-review-prepare`, `kg-review-set`, `kg-review-validate`, `kg-review-export`](#review-existing-candidates-without-another-paid-trial) | Compare each candidate with its source. Approve usable records, exclude incorrect ones and leave uncertain ones as `needs_review`. Record reviewer attribution. Observations/relationships also need eligible approved subjects/endpoints. | `review.json` stores decisions; optional `reviewed.json` exports the approved-only local projection. No Neo4j writes. |
| **5. Stage in Neo4j** | [`make kg-publish`](#publish-the-approved-subset-to-neo4j) | Recheck current PostgreSQL builds and full artifacts; write an immutable snapshot of eligible approved records. **Queries still use the previously active publication, if any.** | A Neo4j publication with status `staged`. The publisher reads authoritative checkpoints and `review.json`, not the optional export. |
| **6. Verify the staged publication** | [`make kg-publication-verify`](#publish-the-approved-subset-to-neo4j) | Compare stored nodes, relationships and provenance with the approved inputs, and recheck PostgreSQL source eligibility. This is a read-only check. | A verification report. The active-publication pointer is unchanged. |
| **7. Activate explicitly** | [`make kg-activate`](#publish-the-approved-subset-to-neo4j) | Verify again, then switch the named graph's active pointer to this publication. A replacement must specify the expected current publication ID. | Status `active`; the previous publication becomes `retired` and is retained, not deleted. |

**Extraction creates candidates; review authorizes records; publication stores them;
activation selects the publication used by retrieval.** These are separate decisions.
`kg-publish-preview` is an optional read-only preflight before staging.

After activation, select **KG** in Streamlit: Hybrid search and bounded graph traversal
recover eligible original source chunks for cited answer generation. KG-Agentic remains
planned. Daily arXiv ingestion and GUI uploads **do not automatically run this KG pipeline**.

**`make kg-extract` currently does not connect to Neo4j.** Its `Neo4jGraph` object is a
serialized staging representation in local candidates, not nodes already in the database.
`make kg-up` only starts the database service. `kg-publish` explicitly writes reviewed
content; `kg-activate` separately switches the active publication. Publication commands
retain the conservative legacy `graph_ready: false` and now report `query_readiness:
not_checked`: they do not exercise runtime Qdrant/model connectivity. Use the actual `kg`
query mode to test query readiness, not that publication-only flag.

The publisher uses stable IDs, uniqueness constraints and transactions for idempotent writes,
preserves hypotheses/uncertainties/conflicting measurements and checks PostgreSQL scope again
before commit/activation. Failed replacements retain the previous active graph. Scientific
records are publication-local, not globally merged entities. Shared paper/build/chunk
references are immutable; source reference sharing must not grant access to another
publication's assertions. Daily KG
automation comes after this construction/activation path has been tested, not before.

## Query the active graph

After publication/activation, no new extraction, embeddings, re-indexing or evaluation
dataset is needed:

```bash
make kg-up
docker compose up -d --build api streamlit-app
```

In Streamlit select **KG — Hybrid + reviewed graph expansion**, source **All ready papers**
or **arXiv**, and ask e.g. “What is reported about 47 Tucanae?” The KG details panel
shows publication identity, eligible graph papers, selected graph-supported chunk count
and `graph_augmented` versus `hybrid_only_no_graph_match`.

The host uses `NEO4J_URI=bolt://localhost:7687`; Compose sets the API to
`NEO4J_URI_CONTAINER` (default `bolt://neo4j:7687`) on the shared application network.
The official Neo4j driver is a base dependency; the heavyweight `kg` extraction group is
not needed in the API image. The other four modes do not connect to Neo4j.

The isolated implementations are `src/api/rag/modes/kg.py` (retrieval composition) and
`src/api/kg/retrieval.py` (read-only graph and eligibility policies):

1. Pin the named active publication; absent/inconsistent/changed publication fails explicitly.
2. Run one existing Hybrid search over the full selected corpus with the same `top_k`.
3. Recheck graph builds against PostgreSQL: paper/build/collection/source/version and manifest
   SHA must match. Live queries require active, ready, undeleted builds. Frozen evaluations
   may use retained **ready**, undeleted builds explicitly in their snapshot, never newer
   replacements outside it. Ineligible graph builds are excluded, not silently broadened.
4. Match reviewed names/aliases as exact normalized word-bounded mentions (case/Unicode and
   punctuation normalization only), and find records supported by Hybrid seed points.
   This is entity **lookup**, not cross-paper entity merging or inferred alias enrichment.
5. Use fixed parameterized Cypher with at most two `HAS_OBSERVATION`/`SUBJECT`/`OBJECT`
   structural links, e.g. entity → relationship assertion → entity. Every intermediate
   node/edge must be in the publication and eligible projection; structural links must agree
   with the approved record endpoints. No generated Cypher, APOC, query writes or LLM planner.
6. Validate approved attribution, dependencies/roles, literal evidence quotes, original chunk
   identity and text hashes. Return full original source chunks, not generated KG statements.
7. Merge Hybrid and graph chunk rankings with RRF (60), reserve one graph-backed slot if
   found, and keep final `top_k`. Recheck SQL eligibility and publication identity. Use shared
   baseline atomic-claim generation and citation checks. These checks do not prove scientific
   entailment; the same independent evaluation judges still apply.

The initial pilot has **86 approved records, but only 4 scientific relationships** across
16 source chunks and 7 papers. The 376 stored edges include provenance; they are not 376
scientific connections. There is no global entity resolution, and two structural links do
not imply arbitrary scientific multihop reasoning. Do not expect universal improvements.
Hybrid-only answers remain explicitly labelled; missing Neo4j is a 503, and a changed pinned
publication is a 409. Start a new conversation after a graph change. Backend memory is
isolated by graph publication as well as the ordinary corpus/mode/model fingerprint.
Cross-store checks are not a distributed transaction; arbitrary admin edits can still race.

Query limits in `.env.sample` / `KGSettings`:

| Setting | Default | Range / meaning |
| --- | ---: | --- |
| `KG_QUERY_MAX_RECORDS` | 2000 | 1–50000; active-publication record bound; fail rather than truncate validation |
| `KG_QUERY_MAX_SOURCE_LINKS` | 20000 | 1–1000000; source-quote validation bound; explicit failure |
| `KG_QUERY_MAX_TEXT_BYTES` | 10000000 | 10000–50000000; unique eligible chunk UTF-8 bytes; explicit failure |
| `KG_QUERY_MAX_CHUNKS` | 20 | 1–50 graph candidates before final `top_k` |
| `KG_QUERY_PUBLICATION_ID` | empty | Optional expected active ID for runtime; otherwise follow active |
| `KG_NEO4J_TIMEOUT_SECONDS` | 30 | 1–300; each Neo4j transaction/connection; no driver retries |

This first pilot reader validates the bounded eligible projection on each request; it is
not yet a large-corpus query optimization. Neo4j traversal syntax follows the official
[bounded path documentation](https://neo4j.com/docs/cypher-manual/current/patterns/variable-length-paths/).

For a paid smoke benchmark, explicitly opt in (same questions/split; no regeneration):

```bash
make eval-run \
  EVAL_REVIEWED=data/evaluation/markdown-mini-v4/questions.split.json \
  EVAL_SPLIT=development EVAL_MODES=kg EVAL_LIMIT=2 EVAL_JUDGE=true
```

The runner pins the active graph **before paid work**, persists its publication/plan/model
revision/manifest and query bounds in `manifest.json`, and requires that same active ID per
item. Optional `EVAL_KG_PUBLICATION_ID=publication:...` asserts an explicit expected ID.
Results/Langfuse retain graph IDs, traversal/coverage/selection diagnostics; summaries expose
graph-used versus Hybrid-only run counts. `kg_hybrid_seconds` and `kg_graph_seconds` report
retrieval sub-stages (they overlap `retrieval_seconds`, not additional total time).
The original four default evaluation modes remain
unchanged. For a five-mode comparison pass
`EVAL_MODES="vanilla hybrid hybrid_rerank agentic kg"`; interpret graph-covered questions
separately from the rest. These tests establish wiring/scope, not a measured quality gain.

Offline tests: `tests/unit/test_kg_retrieval.py`, `test_kg_runtime.py`. The opt-in
`make kg-test-neo4j` also exercises native read-only traversal in a disposable synthetic
database, verifies the publication remains unchanged and excludes deleted sources.

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

Current provider evidence uses **source-span IDs**, not model-written quotations. Before
each request, `spans.py` assigns deterministic IDs (`s001`, `s002`, …) to exact citation
windows inside that existing chunk. The native Pydantic schema exposes only those IDs
as permitted values. The application copies each selected substring verbatim, attaching
the existing paper/build/collection/point/page/section identity. The source windows and
end-exclusive Unicode character offsets are also saved in each result for review.
They are **not new retrieval chunks**, are not embedded and do not change Qdrant IDs.

This removes the need for the model to reproduce Markdown, equations and Unicode exactly.
It does not prove that the selected passage supports the assertion; values/uncertainties,
scientific interpretation and relationship subjects still require review. Missing endpoints
and hypothesis-status violations remain failures, not automatically repaired facts.

Reuse full page-aware Markdown chunks from verified build artifacts. Do not run the
package's default PDF loader/splitter, assign replacement chunk IDs, or regenerate vectors.
Its [Qdrant retriever](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html#qdrant-retrievers)
can map external hits to graph nodes. Its built-in Hybrid retriever, however, uses Neo4j
vector/full-text indexes: it is not our Qdrant dense + BM25 + RRF pipeline. Preserve that
existing pipeline and add bounded graph expansion from its result IDs where appropriate.
Keep the existing generator and citation checks, rather than replacing the application
with the package's complete answer pipeline.

## Scientific schema and per-record validation

`scientific_schema.py` defines the entity/observation/relationship types introduced in v2.
The current stored batch uses `record_schema.py` (`scientific-kg-v3`) and deterministic
holding rules in `quarantine.py`. Earlier v1/v2 contracts remain unchanged for historical
validation; existing pilots are not silently converted.

- **Entity:** astronomical object, stellar population, spatial region, study, analysis,
  model, physical process, method, dataset, instrument or author, with source evidence.
  Physical properties belong in observations, not invented objects/datasets. Keep named
  objects separate; aliases are candidate alternative names, not examples or subclasses
  and not permission to merge objects globally. These are extraction instructions, not
  deterministic proof that an entity was classified correctly.
- **Observation:** measurement, upper/lower limit, simulation result, hypothesis,
  selection criterion, model parameter, adopted value, assumption, planned analysis,
  qualitative finding, method description or theoretical result. Record the subject,
  statement, literal value, units, uncertainty, conditions and quantity dimension.
  Distinguish reported measurements from cuts/settings/plans; qualitative observations
  need no invented number. Numeric observations without a quantity/value are quarantined.
- **Relationship:** uses a method/dataset, observed with an instrument, located in,
  compared with, proposed origin/enrichment, or derived from. Proposed origins/enrichment
  must remain hypotheses. Chemical enrichment is not object parentage.
- **EvidenceReference:** paper, build, collection, point, source, page, section and
  a literal supporting quote. Every entity/observation/relationship needs evidence.
- **ExtractionBatch:** one source build plus extraction model and revision. Record IDs
  are build-local; the writer must namespace them by build/extraction revision.

Different papers or conditions produce separate observations. Never overwrite a measurement
with another paper's value, flatten uncertainties, or promote a proposed explanation into
an established fact. Preserve ambiguous/damaged numerical passages for review; do not guess
missing signs, exponents or digits. The initial model is `gpt-5-mini`, with `low` reasoning
and a 16,384-token completion cap (reasoning plus output), configurable before preparation.

Relationship endpoint roles are checked **after native parsing and before accepting a batch**:

| Predicate | Allowed subject kinds | Allowed target kinds |
| --- | --- | --- |
| `uses_method` | study, analysis, model, dataset, observation | method, model |
| `uses_dataset` | study, analysis, method, model, observation | dataset |
| `observed_with` | astronomical object, stellar population, spatial region, observation | instrument |
| `located_in` | astronomical object, stellar population, spatial region | astronomical object, stellar population, spatial region |
| `compares_with` | astronomical object, stellar population, analysis, model, dataset, observation | same kinds |
| `proposes_origin` | astronomical object, stellar population | astronomical object, stellar population |
| `proposes_enrichment` | observation, physical process | physical process, astronomical object, stellar population |
| `derived_from` | dataset, model, observation | dataset, model |

Here “observation” means an existing observation record ID, not an entity kind.
In v3, invalid roles quarantine the **relationship**, not the whole chunk, with
`invalid_relationship_role` and precise field paths. Missing observation subjects
quarantine that observation and dependent edges; missing relationship endpoints hold
the edge. IDs/records remain unchanged; endpoints are never inferred or redirected.
Independently valid sibling records survive. Historical v2 rejected these errors at
chunk level. Duplicate IDs, malformed typed output and source-identity/provenance
violations still fail the entire chunk; quarantine cannot repair those failures.
Omit a relationship that cannot faithfully fit; do not manufacture a compatible node.
These checks prevent incompatible types, not scientifically false claims with valid types.

### Extraction guidance and final checklist

The prompt in `extraction.py` includes contrasting, illustrative examples:

- A reported numeric distance is a `measurement`; similar rotation or near-solar
  metallicity without a numeric result is a `qualitative_finding`.
- A simulated input grid is a `model_parameter`; a numeric simulated outcome is a
  `simulation_result`. A sample brightness cut is a `selection_criterion`, not an
  observational upper limit. A borrowed radius is an `adopted_value`.
- Assumptions, planned analyses and symbolic theoretical findings are not numeric
  measurements. No numeric value is invented to fill the output fields.
- Tick positions, marker colours and captions merely saying a distribution is plotted
  are omitted. An explicit scientific finding in a caption remains eligible.
- An instrument and its dataset are distinct. A study cannot be physically located
  inside a cluster; a formation mechanism is not object parentage. Omit a relationship
  when the schema cannot faithfully express it, instead of inventing compatible nodes.

Before returning the same structured response, the model is instructed to check kinds,
numeric fields, declared subjects, unique IDs, relationship roles/direction and complete
supporting spans. It must retain ambiguity flags and keep examples separate from source
evidence. This is prompt guidance, **not a second reviewer call**, automatic reclassification
or proof of entailment. Native parsing, rejection/quarantine rules, model defaults and
call/token/concurrency budgets are unchanged. The later record-quarantine upgrade changes
local batch validation/projection, not this provider prompt or native output schema.

Offline mocked-provider tests verify that these kinds survive parsing unchanged, empty
presentation-only outputs are accepted, the revised prompt reaches the provider, and old
checkpoints remain readable. They do not measure a live model's classification quality;
a new, scientifically reviewed paid sample is needed for that comparison. The prompt uses
explicit instructions and examples following [official OpenAI prompting guidance](https://developers.openai.com/api/docs/guides/prompt-engineering).

### Numeric quarantine, not automatic correction

`quality_flags` preserve model-reported ambiguity in numbers, units, uncertainty, evidence
or source conflicts. Local checks additionally flag missing numeric quantities/values,
non-descriptive quantity names, control characters, ambiguous bracketed numeric fragments,
and a declared inverse-time quantity paired with a bare time unit (for example a rate in
`Myr`). No units, exponents or uncertainties are silently repaired.

Flagged observations and their dependent relationships remain intact in the source `batch`
inside `candidates.json`, with a per-chunk `quarantine` list. They are **excluded from the
local staged `graph`**, while unaffected observations survive. Validation recomputes this
projection and rejects mismatched graph/quarantine records. `quarantined_records` counts
both held observations and dependent relationships. `complete` means extraction finished,
not that every assertion is scientifically usable or approved.

The unit check covers a narrow dimensional conflict, not all dimensional algebra, and
depends on the extracted dimension. Bracketed fragments may include legitimate source
notation; conservative quarantine asks for review rather than guessing. Exact span quotes
still need scientific entailment review. Resolving a flagged number requires checking the
full relevant source passage/table, preserving its provenance; flags must not simply be
cleared to publish a guess. Local approval/exclusion is available below; numeric correction
and Neo4j publication remain unimplemented.

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
make kg-schema            # Inspect stored scientific records (provider span-ID enum is chunk-specific)
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

### Continue after the record-quarantine upgrade

The old `pilot-v1` trial used model-written quotations; `pilot-spans-v2` introduced exact
source-span IDs but still used schema v1. `pilot-schema-v3` uses scientific schema v2;
its sample exposed remaining classification mistakes. `pilot-guidance-v4` improved
guidance but still rejected whole chunks on bad links. All four pilots remain readable.
Batch schema v3 introduces a versioned record-quarantine policy and requires a **new
output directory** for future paid extraction. Review existing v4 successes now without
another model call (see below). Old failed requests saved no rejected record bodies;
their valid siblings cannot be recovered retroactively. Do not overwrite old plans,
approvals or mix revisions.

```bash
# Free: existing successes remain readable; no new extraction in this legacy directory.
make kg-validate KG_DIR=data/knowledge_graph/pilot-v1
make kg-validate KG_DIR=data/knowledge_graph/pilot-spans-v2
make kg-validate KG_DIR=data/knowledge_graph/pilot-schema-v3
make kg-validate KG_DIR=data/knowledge_graph/pilot-guidance-v4

# Optional later trial: freeze the same seven papers for per-record quarantine.
make kg-prepare KG_DIR=data/knowledge_graph/pilot-records-v5

# PAID: fresh three-chunk sample from each paper (21 requests maximum).
make kg-extract KG_DIR=data/knowledge_graph/pilot-records-v5 \
  KG_CHUNKS_PER_PAPER=3 KG_MAX_CALLS=21
make kg-validate KG_DIR=data/knowledge_graph/pilot-records-v5
```

Old results are retained for comparison, **not silently converted or auto-approved**.
The new trial can reprocess previously sampled chunks and incurs separate model costs.
There is no PDF re-extraction, vector re-indexing or evaluation-set regeneration.
Validation reports `legacy_chunks` separately from `semantic_schema_checked_chunks`;
v1 legacy validity is source/structural integrity, not passage of v2 semantic checks.
`pilot-schema-v3` and `pilot-guidance-v4` retain their v2 role/quarantine/span checks and
are counted under `semantic_schema_checked_chunks`, despite older revisions. None of these counters
constitutes scientific approval or graph activation.
Review the new sample before widening the paper scope. More papers improve coverage and
test generality, but cannot fix systematic typing/provenance errors in existing extraction.

### Review existing candidates without another paid trial

```bash
make kg-review-prepare KG_DIR=data/knowledge_graph/pilot-guidance-v4
```

This creates **`review.json`**, a separate editable sidecar from validated SQLite
checkpoints—not a possibly edited `candidates.json`. Entries contain the original record,
source quotes, scoped IDs and quarantine reasons. All start as `needs_review`; nothing
is auto-approved/excluded. Repeating preparation preserves decisions and formatting.

After checking an entry, edit only its decision fields, or use:

```bash
make kg-review-set KG_DIR=data/knowledge_graph/pilot-guidance-v4 \
  KG_RECORD_ID="<full record_id copied from review.json>" \
  KG_DECISION=excluded KG_REASON=presentation_only KG_REVIEWER="Philippe"
```

| Field | What to enter |
| --- | --- |
| `decision` | `approved`, `excluded`, or leave `needs_review` |
| `reviewer` | Reviewer name, required for approved/excluded decisions |
| `reason` | Exclusions require `presentation_only`, `unsupported`, `incorrect_type`, `duplicate`, or `other`; approvals use `null` |
| `notes` | Optional explanation (`KG_NOTES` in Make) |

Use `presentation_only` for legends/ticks/purely graphical descriptions, not a scientific
finding just because it occurs in a caption. Do not automatically exclude every caption
or bulk-approve all records. Approving an entity does not approve its observations/edges.
Quarantined records **cannot be approved**; retain or exclude them. Do not rewrite raw
numbers, clear flags or change `record`, IDs or quarantine metadata to bypass checks.

```bash
make kg-review-validate KG_DIR=data/knowledge_graph/pilot-guidance-v4
make kg-review-export KG_DIR=data/knowledge_graph/pilot-guidance-v4
```

Validation checks reviewer attribution, exact record-set/content integrity and frozen
candidate fingerprint alongside extraction provenance. Export writes **`reviewed.json`**,
never checkpoints/candidates, with decisions and an approved-only local graph projection.
Observations also need their subject approved; relationships need both eligible endpoints
approved. Held approvals are listed under `approved_but_dependency_held`. Partial reviews
may export; unreviewed records never enter that projection. `review_complete` concerns
the candidate set, not the entire corpus. `graph_ready` remains false; no review command
connects to Neo4j or activates a graph.

Further extraction that changes the completed candidate set makes an old review stale.
Use `KG_REVIEW=review-batch2.json` to prepare a fresh sidecar; previous decisions are not
overwritten or automatically copied. Only separate local JSON filenames are accepted.

## Publish the approved subset to Neo4j

The current reviewed pilot has 86 eligible records (41 entities, 41 observations, four
scientific relationships). The 23 exclusions and 50 unresolved records stay out. Partial
review/extraction is allowed; publication does not claim complete paper/corpus coverage.

```bash
make kg-up

# PostgreSQL + full artifact checks only; no Neo4j writes or model calls.
make kg-publish-preview KG_DIR=data/knowledge_graph/pilot-guidance-v4

# Writes a staged snapshot, without replacing the active one.
make kg-publish KG_DIR=data/knowledge_graph/pilot-guidance-v4
make kg-publication-verify KG_DIR=data/knowledge_graph/pilot-guidance-v4
```

Inspect the staged data in Neo4j Browser (http://localhost:7474) before activating:

```cypher
MATCH (p:KGPublication)
RETURN p.id, p.graph_name, p.status, p.manifest_json;
```

First activation is explicit and requires that this graph name has no current publication:

```bash
make kg-activate KG_DIR=data/knowledge_graph/pilot-guidance-v4
make kg-publication-status
```

For replacement, copy the current ID from status and use
`make kg-activate KG_DIR=... KG_EXPECT_ACTIVE="publication:<current-id>"`.
Activation fails if the expected pointer no longer matches. Repeating activation of the
already-active exact snapshot is safe. Old publications become `retired`, but their
records remain intact; failed stages/verifications/activations cannot replace them.
`KG_GRAPH=another-name` overrides the configured graph name on these commands. Use the
same name for preview, publication, verification, activation and status.

### Integrity and transaction boundaries

`publication.py` rebuilds the approved projection from validated authoritative checkpoints
and `review.json`; it does **not** trust or require `reviewed.json`. A review/decision,
source snapshot or writer-version change yields a new content-derived publication ID.
Repeating the same publication checks the existing exact graph rather than creating
duplicates, repairing corruption or demoting active content.

Publication/verification/activation hold the existing PostgreSQL ingestion advisory lock
and a local directory lock. Each selected paper must still be active, ready, undeleted,
in the exact collection/version/source, with the frozen manifest hash. Full artifact
hashes, text, page/section/point identity and chunk order are rechecked before writing.
Retained-but-inactive builds are not publishable through this live-corpus workflow.
If ingestion holds the writer lock, retry later. Stale sources fail closed; no silent
build substitution, reindex, review transfer or scope expansion occurs.

`neo4j_store.py` uses the [official Python driver's explicit transactions](https://neo4j.com/docs/python-manual/current/transactions/)
and [uniqueness constraints](https://neo4j.com/docs/cypher-manual/current/schema/constraints/create-constraints/).
Values are parameters; labels/predicates come from static application allowlists. No
APOC, model-generated Cypher or GraphRAG default entity-resolution step is involved.
All pilot data writes and their exact content/provenance audit are one bounded transaction.
Source eligibility is checked again before commit. Schema constraints are a separate,
idempotent transaction and may remain after a failed data stage; they expose no facts.
There are no implicit transaction retries. An interrupted commit can have an unknown
outcome; repeat the identical command to verify/reuse it safely.

Activation takes a Neo4j write lock on `KGCorpus`, verifies every stored node/edge against
the approved projection, and atomically switches the pointer/statuses. Normal catalogue
writers share the PostgreSQL advisory lock; this is **not** a distributed transaction
against arbitrary direct SQL/admin mutations. Eligibility is only certified at command
time. Future retrieval must recheck PostgreSQL and filter by the active publication and
its allowed source builds on every request; activation is not permanent scope authority.
`kg-publication-status` reads metadata only, reports `catalogue_checked: false`, and
lists up to 50 publications with an explicit `history_truncated` flag. It is not a content
or SQL-source audit; use `kg-publication-verify` for that.

### Stored model

| Label | Purpose |
| --- | --- |
| `KGCorpus` | Named active-publication pointer |
| `KGPublication` | Immutable manifest/counts/fingerprints plus staged/active/retired status |
| `KGPaper`, `KGSourceBuild`, `KGChunk` | Immutable original identities, manifest reference, full source text, point/page/section/ordinal |
| `KGRecord:KGEntity` | Reviewed, publication-local entity and candidate aliases |
| `KGRecord:KGObservation` | Attributed statement, raw values/units/conditions, extraction model/revision and reviewer |
| `KGRecord:KGRelationship` | Reviewed relationship assertion, endpoints and epistemic status |

Each assertion has `SUPPORTED_BY` edges carrying exact quote/evidence metadata to its
original `KGChunk`. `HAS_OBSERVATION` links entities to observations. Scientific edges
(for example `LOCATED_IN`) link reviewed endpoints and point back to their first-class
relationship assertion with `assertion_id`. Source/reference edges carry publication IDs.
Thus **four scientific relationships are not the total edge count**: most edges preserve
membership, source identity or evidence. Counts expose both quantities.

Aliases are stored as reviewed candidates, not merged automatically. Even identically
named scientific entities in different chunks/publications remain distinct. Conservative
entity resolution and useful graph retrieval are subsequent work, not demonstrated by
loading this small provenance-first graph. No KG quality improvement is claimed.

### Publication configuration and tests

Merge relevant settings from `.env.sample` into your existing `.env`; never overwrite it.
Defaults target the optional local container. A changed password variable does not reset
an initialized Neo4j database password.

| Setting | Default | Meaning / enforced range |
| --- | --- | --- |
| `NEO4J_URI` | `bolt://localhost:7687` | Host CLI connection; Compose-network clients use `bolt://neo4j:7687` |
| `NEO4J_USERNAME` / `NEO4J_PASSWORD` | `neo4j` / `neo4j-local-only` | Local-only credentials |
| `NEO4J_DATABASE` | `neo4j` | Explicit target database |
| `KG_GRAPH_NAME` | `star-clusters-pilot` | 1–64 letters/digits/dot/underscore/hyphen; starts with letter/digit |
| `KG_NEO4J_TIMEOUT_SECONDS` | 30 | 1–300; transaction/connection timeout, not whole-command artifact-read deadline |
| `KG_PUBLISH_MAX_RECORDS` | 10000 | 1–50000; eligible reviewed records per atomic publication |
| `KG_PUBLISH_MAX_BYTES` | 10000000 | 10000–50000000; serialized approved content bytes, not a model budget |

Limits fail explicitly, never truncate assertions. The atomic writer is intended for
bounded pilots, not unlimited bulk graph import. PostgreSQL catalogue and Qdrant are not
modified; publication requires no model API key and performs no embedding or inference.

`make kg-test` tests policy and the actual driver adapter with a transactional test double.
For native Cypher/transaction tests, run `make kg-test-neo4j`: it starts a separate randomly
named disposable container from the already-present pinned image (no image pull), uses
synthetic data/no `.env`, and removes that container afterward. It does not use Compose
or touch an existing database. Tests cover staging/verification, idempotence, activation,
replacement/CAS safety, source rejection, provenance drift and rollback.

## First run or fresh extraction pilot

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
intentional until explicit review and publication. Neither extraction nor validation
automatically calls the separate review/publication commands.

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
- `invalid_relationship_role`: the referenced node has an incompatible type for that
  predicate's subject/target (allowed and actual kinds are recorded).

Paths use **zero-based** list indices. SDK schema/truncation/refusal diagnostics remain separate.
In v3, link/role issues appear in per-record quarantine reasons/paths and a terminal
quarantine count instead of chunk failure. `complete` may therefore include held records;
it is not scientific approval. Fatal source/identity/typed-output failures remain separate.
Record text, quotation contents, raw validation inputs and exception messages are not saved
in rejection logs; token usage and provider model/response ID are retained when available.
Every retry remains a paid, explicit request; the validation checks are unchanged.

`quote_not_found` is a legacy quote-based failure. Current extraction selects schema-enforced
span IDs; an invalid ID is rejected by native parsing at an `evidence.*.span_id` field.
Application-side `unknown_source_span` also guards source binding. Quotes in accepted records
come only from the selected windows, never from model-retyped text. Rejecting a selected
span does not authorize fuzzy quote matching, silent numeric repair or weaker scope checks.

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
  certify that those builds are still active; the publisher and future retriever must recheck
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
HTTP responses, plus hash/scope validation, refusal/failure handling, resumption,
relationship-role rejection, numeric quarantine and checkpoint tampering checks.
Tests also cover per-record link quarantine, presentation exclusions, attribution,
dependency holding, stale/tampered reviews and historical compatibility.
It makes no paid requests and writes no external databases. Normal `make test` skips
optional extraction tests if the `kg` group is absent.

See [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
for native typed parsing. Schema conformance is not a substitute for scientific review.

## Remaining implementation slices

1. **Offline extraction (implemented):** verified full artifacts, typed library component,
   explicit paid command, bounded parallelism, local checkpoints and optional Langfuse.
   Record scientific decisions with `kg-review-*` and export a local approved-only
   projection before graph persistence. Scientific decisions remain manual and fallible.
   No daily automation yet.
2. **Graph persistence (implemented):** constraints, immutable reviewed snapshots,
   exact content/provenance verification and explicit CAS-guarded activation. Failed
   replacements retain the old graph. Source references are immutable; scientific records
   stay publication-local. Conservative entity/alias resolution remains subsequent work.
   PostgreSQL remains authoritative, and every retrieval rechecks eligibility.
3. **Deterministic KG mode (implemented):** Hybrid seeds + bounded, parameterized read-only
   graph queries return original supporting chunks under the same scope. Separate mode,
   API, UI and frozen runner integration; no LLM-generated Cypher. Next: controlled coverage
   and quality benchmarks, then scaling/entity-resolution work.
4. **KG-Agentic:** add the tested graph tool to existing LangGraph orchestration without
   changing the four existing modes; record paths, supporting IDs and stage latency.
5. **Comparison and daily integration:** reuse reviewed questions, add genuinely relational
   human-reviewed questions, pin graph extraction/build identity in frozen evaluations and
   compare identical paper scopes. Integrate incremental extraction only after validation.

During the pilot, do not compare a seven-paper graph against unrestricted 48-paper retrieval
as if their coverage were equal. Graph incompleteness is not evidence that a fact is absent.
No vector re-indexing or wholesale evaluation regeneration is inherently required; existing
point IDs and approvals remain untouched. No KG quality/latency improvement is claimed yet.
