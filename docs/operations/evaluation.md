# Evaluation

Recorded benchmark outcomes are kept in [Evaluation results](evaluation-results.md).

## Generate a first question set

From the repository root, with PostgreSQL and Qdrant reachable using your host `.env`:

```bash
make eval-preview             # Freeze evidence and show the plan; NO model calls
make create-eval-dataset      # Paid OpenAI generation from that saved preview
```

The default samples up to **50 active arXiv papers**, four text excerpts per paper,
and plans **50 candidates**: 30 single-paper, 15 cross-paper, and 5
insufficient-evidence cases. Within those broad kinds, new plans label direct facts,
within-paper synthesis, cross-paper comparison, cross-paper multihop and unanswerable
profiles. It uses `gpt-4.1-mini` and your `OPENAI_API_KEY`.
Neither command changes PostgreSQL/Qdrant, ingests papers, or publishes an experiment.
No RAGAS, Groq, Cohere or Langfuse credentials are needed for question generation.

Look in `data/evaluation/star-clusters/`:

- `snapshot.json`: sampled text, titles, page numbers when available, collection/point
  IDs, paper/version/build identity and the active-corpus fingerprint.
- `plan.json`: frozen question types, evidence groups, prompt, model and limits.
- `results.json`: submission journal, saved background response IDs/statuses and terminal
  outputs, plus completed candidates/rejections and token usage.
- `questions.json`: candidate questions, reference answers, cited source excerpts,
  evidence IDs and `review_status: needs_review`.

The snapshot is a **sample of indexed text**, not a full corpus backup. Preview respects
the configured arXiv category/topic scope and embedding model, so its paper count may
be lower than `make papers-count` (which includes uploads and all ready builds).
It reads only manifest-listed points belonging to active builds, excludes figures and
generated summaries, and fails on missing points or identity drift. Legacy upload
adoption relies on its observed manifest. Use `make papers-audit` for vector validation.

### Evidence and answerability checks

New previews favour Methods, Results, Discussion and Conclusions, then fill remaining
slots from other usable text. References, acknowledgments, funding text, citation-list
dominated chunks and empty figure placeholders are excluded using headings and text
heuristics. Substantive figure captions remain eligible. Sampling is seeded within each
priority; snapshots retain the original excerpt text, `section_header`, `content_kind`
and `selection_priority` (0 preferred, 1 fallback). Papers without eligible excerpts are
listed in `excluded_no_text_build_ids`; previews may contain fewer papers than requested.

The prompt first identifies a supported fact, then asks a question that the fact answers.
Every question must include its paper's full title (both titles for a comparison), except
the `metadata_discovery` profile: its question hides the title while its answer names it.
New plans freeze `quality_policy: fact-first-v1`. That policy rejects answerable jobs
whose reference answers explicitly abstain or say necessary information is missing,
and rejects questions missing paper titles or referring to supplied excerpts. These
checks use text heuristics: inspect rejections and review accepted drafts for scientific
correctness. They do not prove that a cited excerpt supports every claim.

Older plans retain their prior validation behaviour. Keep the earlier pilot and create a
new directory to apply these changes, for example:

```bash
make eval-preview EVAL_DIR=data/evaluation/markdown-mini-pilot-v3 \
  EVAL_MODEL=gpt-5-mini EVAL_REASONING_EFFORT=minimal \
  EVAL_MAX_TOKENS=4000 QUESTIONS=10 PAPERS=20
make create-eval-dataset EVAL_DIR=data/evaluation/markdown-mini-pilot-v3
```

Review these ten drafts before creating the full set. `needs_review` means the automatic
checks passed; it does not mean the question is verified as answerable. Abstention tests
remain scoped to the sampled excerpts until a reviewer checks the whole corpus.

### Customize or create another set

```bash
make eval-preview EVAL_DIR=data/evaluation/pilot QUESTIONS=10 PAPERS=20
make create-eval-dataset EVAL_DIR=data/evaluation/pilot
```

Preview also accepts `EVAL_SOURCE=arxiv|uploads|all`, `EVAL_MODEL=...`, `EVAL_SEED=42`
and `EVAL_MAX_TOKENS=2500` (per-call cap; allowed range 256–128000).
The CLI `python -m evals.generate_questions prepare --help` exposes all options.
At least two papers with usable text are required. Preview never overwrites an existing
directory: choose a new `EVAL_DIR` for a new sample, model or question count.
Sampling is deterministic for unchanged inputs and seed; model responses need not be.

### Agentic-ready v3 set

For the next Agentic RAG milestone, create a **new** 70-question plan over the current
50-paper corpus. This deliberately increases questions that require synthesis, iterative
retrieval and abstention:

```bash
make eval-preview \
  EVAL_DIR=data/evaluation/markdown-mini-v3 \
  QUESTIONS=70 PAPERS=50 \
  EVAL_MODEL=gpt-5-mini EVAL_REASONING_EFFORT=minimal \
  EVAL_MAX_TOKENS=4000 \
  EVAL_SINGLE_FACT=20 \
  EVAL_SINGLE_SYNTHESIS=10 \
  EVAL_CROSS_COMPARISON=15 \
  EVAL_CROSS_MULTIHOP=10 \
  EVAL_METADATA_DISCOVERY=5 \
  EVAL_UNANSWERABLE=10
```

This preview makes no model calls. Its planned aggregate is 35 single-paper questions,
25 cross-paper questions and 10 unanswerable candidates. The profiles mean:

| Profile | Count | Retrieval challenge |
| --- | ---: | --- |
| `single_fact` | 20 | One precise fact from one paper |
| `single_synthesis` | 10 | Combine at least two excerpts from one paper |
| `cross_comparison` | 15 | Compare supported findings or methods from two papers |
| `cross_multihop` | 10 | Retrieve from both papers and perform an explicit synthesis step |
| `metadata_discovery` | 5 | Identify a study from metadata/topic clues, then answer from it |
| `unanswerable` | 10 | Detect missing evidence and abstain |

Cross-paper jobs use topical title/abstract overlap and disjoint pairs before any pair is
reused. With 50 eligible papers and 25 cross-paper jobs, this creates 25 two-paper
components, making a later paper-group development/test split feasible.

Inspect `plan.json` and `snapshot.json`, then explicitly start the paid generation:

```bash
make create-eval-dataset \
  EVAL_DIR=data/evaluation/markdown-mini-v3 \
  EVAL_WAIT_SECONDS=600
```

Generated profile labels flow into the reviewed dataset, benchmark result records,
Langfuse items/traces and the run manifest's `question_profiles` counts. They let reports
be broken down by retrieval challenge instead of only `single_paper`/`cross_paper`.
The generator still cannot create independent human-authored questions: add 5–10 real
research questions during review, either replacing weaker synthetic drafts or expanding
the set. Every generated item remains `needs_review`.

### Fast GPT-5 Mini pilot

For this bounded, excerpt-grounded JSON task, start with a small `gpt-5-mini` pilot and
minimal reasoning before paying for a full dataset:

```bash
make eval-preview EVAL_DIR=data/evaluation/markdown-mini-pilot \
  EVAL_MODEL=gpt-5-mini EVAL_REASONING_EFFORT=minimal \
  EVAL_MAX_TOKENS=4000 QUESTIONS=10 PAPERS=20
make eval-check EVAL_DIR=data/evaluation/markdown-mini-pilot
make create-eval-dataset EVAL_DIR=data/evaluation/markdown-mini-pilot EVAL_WAIT_SECONDS=600
```

`EVAL_REASONING_EFFORT` is optional and is sent only when set. It is saved in `plan.json`,
so it cannot be changed after generation begins; use a new directory to compare models or
effort. Choose only an effort supported by the selected model. `gpt-5-mini` is designed
for well-defined, precise, high-volume work; see the [official model documentation](https://developers.openai.com/api/docs/models/gpt-5-mini).

For GPT-5, allow more room for reasoning and the answer:

```bash
make eval-preview EVAL_DIR=data/evaluation/gpt5 EVAL_MODEL=gpt-5 EVAL_MAX_TOKENS=25000
make create-eval-dataset EVAL_DIR=data/evaluation/gpt5
```

Use a new directory if you already made a preview with the old limit. The model and
token cap are saved in `plan.json` and shown in the preview summary; generation uses
those saved values. Passing `EVAL_MAX_TOKENS` to `create-eval-dataset` does not override
an existing plan. No existing previews or checkpoints are changed automatically.

The cap includes both reasoning and visible output tokens, as described in the
[OpenAI reasoning guide](https://developers.openai.com/api/docs/guides/reasoning).
25,000 is a starting budget, not guaranteed usage or guaranteed success. Raising the
cap permits more spending per question; it does not force the model to use all tokens.
The model must support your chosen limit and Responses API background generation.
The saved token cap is sent as `max_output_tokens`.

Cross-paper partners are chosen greedily by title/abstract word overlap without embeddings;
new profiled plans keep pairs disjoint until all eligible papers have been paired.
This is a simple starting heuristic, not a knowledge graph or a guarantee of meaningful
scientific overlap. Unsupported pairs can be skipped; duplicate questions, unknown
evidence IDs and invalid paper counts are rejected. Thus **50
planned questions can yield fewer than 50 candidates**. Inspect the rejection entries.

The generator validates cited evidence IDs against the frozen snapshot and saves the full
cited excerpts in `reference_evidence`. It deliberately does not ask the model to reproduce
an “exact quote”: PDF-derived Markdown makes that brittle and a copied substring would not
prove the reference answer is correct. Human review verifies that the answer follows from
the saved evidence.

### Costs and resuming

Preview is free of model calls, but reads your databases and saves local excerpts.
Generation sends those excerpts to OpenAI: for private uploads, ensure that is appropriate.
There is at most one new generation submission per unfinished planned question per invocation,
no automatic SDK retries, up to eight excerpts of 2,400 characters per default cross-paper call,
and a default 2,500 completion-token limit per call (override with `EVAL_MAX_TOKENS`
at preview time). These are bounds, not an exact dollar cap.

Generation now uses **background processing with short polling requests**, avoiding a
single connection held open throughout GPT-5 reasoning. Each HTTP request has a maximum
20-second timeout; pending jobs are polled every five seconds for up to 600 seconds per
question per invocation. Override the polling budget with `EVAL_WAIT_SECONDS=1200`
(allowed range 5–3600). Reaching this limit does not cancel the remote job.

Repeating `make create-eval-dataset` resumes saved response IDs without submitting those
questions again. Completed results, including rejections from the previous synchronous
generator, are skipped. Existing previews remain usable without changing their model,
token cap or evidence; new results record `transport: responses-background-v1`.
A fully completed run makes no API calls. Keep snapshots and plans unchanged once
generation starts; their hashes guard resumption.

Requests use `background=true, store=false`. Background execution still requires temporary
server-side storage, roughly ten minutes according to the
[OpenAI background guide](https://developers.openai.com/api/docs/guides/background).
Resume promptly: a saved ID is not a permanent recovery guarantee. Terminal answer text
and usage are saved locally before validation so locally cached responses survive expiry.

Only one generator may use an output directory at a time. After a hard crash, a
`.generating` lock may remain: confirm no generator is running before removing that
specific lock file and resuming. `questions.json` is rebuilt on successful completion;
interrupted results are available in `results.json`. Work in a **copy** when reviewing,
since the convenience export is rebuilt on reruns. Output is under git-ignored `data/`.

## Connection failures

If generation repeatedly fails, check connectivity without spending generation tokens:

```bash
make eval-check EVAL_DIR=data/evaluation/gpt5
```

This makes one read-only request for the saved model's metadata (20-second timeout,
no automatic retries). It does not send paper excerpts or modify evaluation files.
Success confirms metadata access at that moment, not that a longer generation request
will succeed. Background submission and polling also need working connectivity; they
avoid long-held connections but cannot guarantee that a VPN/proxy will allow traffic.

For an interrupted poll or a polling wait limit, rerun the usual command promptly:

```bash
make create-eval-dataset EVAL_DIR=data/evaluation/gpt5
```

If submission was interrupted **before its response ID was saved**, the outcome is unknown:
the request might already be running or billed. The generator stops instead of silently
submitting again. It also stops on expired/unavailable IDs or terminal failed, incomplete
or cancelled responses. Review API activity and the saved job status first. To explicitly
authorize another paid submission for that unresolved job:

```bash
make create-eval-dataset EVAL_DIR=data/evaluation/gpt5 RETRY_JOB=q0002
```

Use the job ID reported by the error. This archives the previous attempt in `results.json`;
it can duplicate spending and is **not** an exactly-once guarantee. It cannot regenerate
completed candidates/rejections or replace a still-retrievable pending job. Old connection
failures from the synchronous generator have no background ID; their unfinished questions
use background submission on the next ordinary run, without `RETRY_JOB`.

Failures now report cause types, numeric error codes when available, a diagnostic
category and a hint. No exception messages, credentials, headers, URLs or paper text
are printed. Generation failures also save `last_error.json` with the question ID,
timestamp and elapsed seconds. This file describes the **last failure**, not current
run status; existing plans and response checkpoints remain unchanged. Share that
diagnostic output instead of repeatedly retrying blindly. After addressing the cause,
resume with `make create-eval-dataset EVAL_DIR=data/evaluation/gpt5`.

Error classification follows [OpenAI's error documentation](https://developers.openai.com/api/docs/guides/error-codes);
`APIConnectionError` alone does not establish a timeout or token-limit problem.

## Review before benchmarking

All generated answers are **synthetic drafts, not verified ground truth**. Evidence-ID
validation proves that the cited frozen excerpts were selected, not that the answer follows
from them.

1. Verify every answer against the excerpts and original paper; correct units, conditions
   and scientific claims. Reject trivial, ambiguous or near-duplicate questions.
2. Check that cross-paper questions genuinely require both papers. A citation to each
   paper alone does not prove a multi-step reasoning requirement. For `cross_multihop`,
   verify that one-paper evidence cannot answer the question and that the answer actually
   performs the requested synthesis.
3. For `single_synthesis`, verify that the cited excerpts contribute distinct necessary
   facts. For `metadata_discovery`, verify that the clues are sufficient without leaking
   the title and that the answer identifies the correct paper.
4. Treat `unanswerable_candidate` as unanswerable **only in the supplied excerpts**.
   Search the full frozen corpus before accepting it as a corpus-level abstention test.
   Its reference evidence is empty; its generation evidence remains in the snapshot.
5. In a separate reviewed copy, mark accepted records `review_status: approved` and
   rejected records `rejected`. Add a few real questions of your own to reduce synthetic bias.
6. Separate development and held-out test papers **before tuning**; connected cross-paper
   groups must stay in one split. Keep the same approved questions and corpus when
   comparing Vanilla, Hybrid, Hybrid + Rerank, Agentic and future graph modes.

### Reviewed dataset contract and splits

Historical schema-v1 reviewed files remain runnable with `EVAL_SPLIT=all`. New benchmark
datasets should use schema v2. Change the copied review file's top-level `schema_version`
to `2`, and add review evidence to every decision. For an approved answerable question:

```json
"review": {
  "reviewer": "reviewer-1",
  "reviewed_at": "2026-09-15T12:00:00Z",
  "decision": "approved",
  "original_sources_checked": true,
  "corpus_search_verified": false
}
```

Rejected records use `decision: rejected`. An approved `unanswerable_candidate` must also
use `answerability_scope: frozen_corpus` and `corpus_search_verified: true` after the
reviewer searches the complete frozen Qdrant builds. The validator rejects excerpt-only
negative cases, missing reference evidence, cross-paper evidence from fewer than two
papers, unknown paper/build identity, duplicate questions and inconsistent review metadata.

Assign a deterministic development/test split after review:

```bash
make eval-split EVAL_DIR=data/evaluation/markdown-mini-v2 \
  EVAL_SPLIT_OUTPUT=data/evaluation/markdown-mini-v2/questions.split.json
make eval-validate \
  EVAL_REVIEWED=data/evaluation/markdown-mini-v2/questions.split.json
```

The split operation derives each question's `paper_ids`, connects papers used by the same
cross-paper question, and assigns whole connected components to one split. It never
overwrites its input. If every reviewed question belongs to one connected paper component,
a leakage-safe two-way split is impossible and the command fails. `EVAL_TEST_RATIO=0.25`
and `EVAL_SEED=42` control a new assignment; both are recorded with the actual resulting
ratio in the output.

Use the development split while changing retrieval or prompts:

```bash
make eval-run EVAL_REVIEWED=data/evaluation/markdown-mini-v2/questions.split.json \
  EVAL_SPLIT=development EVAL_JUDGE=true
```

Run `EVAL_SPLIT=test` only for a held-out comparison. The run manifest records the complete
reviewed-dataset hash, selected split and hash of the exact ordered question IDs. The split
cannot eliminate leakage from prior human/model exposure to the papers; it prevents the
more direct error of tuning and reporting on questions connected to the same papers.

## Run the reviewed benchmark

Start with a two-question smoke run. This makes embedding and answer-generation calls;
the optional judge adds one more model call per answer.

```bash
make eval-run EVAL_DIR=data/evaluation/markdown-mini-v1 EVAL_LIMIT=2
```

Then run all approved questions through all four implemented modes with semantic scoring:

```bash
make eval-run EVAL_DIR=data/evaluation/markdown-mini-v1 EVAL_JUDGE=true
```

Each invocation creates a new directory under `data/evaluation/runs/` containing:

- `manifest.json`: exact dataset, corpus build IDs, models and settings;
- `results.json`: checkpointed per-question answers, retrieved chunks, citations and scores;
- `summary.json` and `report.md`: aggregate four-mode comparison.

The runner ignores non-approved records and queries the **frozen build IDs** saved in
`snapshot.json`, not whatever papers happen to be active after later daily ingestion.
It fails if the reviewed file does not match that snapshot or if its embedding model
differs from the configured query embedding model. Retained Qdrant builds must therefore
remain available while a benchmark snapshot is in use.

The build filter freezes which chunks are eligible, but Qdrant's BM25 `IDF` statistics are
collection-wide. Adding or retaining points in that collection can therefore slightly
change sparse scores even for a frozen build set. For a final repeatable comparison, pause
ingestion for the run (or clone/snapshot the Qdrant collection); record this limitation when
comparing runs made at different times.

The default `EVAL_MODES` is `vanilla hybrid hybrid_rerank agentic`. Override it to isolate a
change, for example `EVAL_MODES="hybrid hybrid_rerank"`. `hybrid_rerank` requires Cohere;
plain `hybrid` does not. Agentic also requires PostgreSQL because its paper-discovery tool
uses the catalogue, while its Qdrant scope remains frozen to the snapshot.

Snapshots made against a dense-only collection cannot exercise BM25 sparse retrieval. After
migrating to the v2 dense+sparse collection, generate and review a new evaluation dataset.
Keep old datasets/runs as historical baselines rather than rewriting their point IDs or
snapshot hashes.

Without the judge, the report contains deterministic retrieval and citation measures.
`EVAL_JUDGE=true` adds correctness, groundedness and answer-relevance scores using
`gpt-5-mini` with minimal reasoning by default. Override with
`EVAL_JUDGE_MODEL` or `EVAL_JUDGE_REASONING_EFFORT`. Gold-citation recall is deliberately
strict: a valid alternative passage may support an answer but still score as a miss.

| Metric | Meaning |
| --- | --- |
| `retrieval_hit` | At least one reviewed reference point was retrieved |
| `retrieval_recall` | Fraction of reviewed reference points retrieved |
| `gold_citation_recall` | Fraction of reviewed reference points selected as citations by the answer model |
| `citation_from_retrieval` | Fraction of selected citation IDs that came from the retrieved set |
| `answer_correctness` | Judge comparison with the reviewed reference answer/evidence |
| `groundedness` | Judge assessment that answer claims follow from retrieved evidence |
| `answer_relevance` | Judge assessment that the answer addresses the question |
| `correct_abstention` | For accepted unanswerable cases, whether the answer declined to invent information |

Judge metrics use `0`, `0.5`, or `1`; they are model assessments, not human ground truth.
Errors are retained per item, processing continues, and the final manifest becomes
`completed_with_errors`. Partial results survive a stopped process, but automatic resume
of an interrupted benchmark run is not implemented yet; a new invocation creates a new run.
OpenAI answer generation and judge calls each make at most one additional call when a
structured model response fails local validation. Judge metadata records both response IDs
and combined usage when that recovery occurs. Other service failures are not retried by the
runner.

`EVAL_MODES="vanilla"`, `EVAL_SPLIT=development`, `EVAL_TOP_K=10`,
`EVAL_GENERATION_MODEL=...`, and `EVAL_CONCURRENCY=...` are available for controlled experiments. Use concurrency 1
until provider rate limits are understood.
Use `EVAL_QUESTION_ID=q0033` to reproduce one approved item from the selected split without
rerunning the whole benchmark; this still performs paid generation and optional judge calls.

Schema-v1 datasets have no split metadata. Do not tune repeatedly on all of their approved
questions and then describe the same scores as held-out performance.

## Track runs in Langfuse

Enable Langfuse as described in [Observability](observability.md). The same `make eval-run`
then uploads the reviewed set to a content-addressed Langfuse Dataset and records every
selected mode as a separate Dataset Experiment. Stable dataset-item IDs make synchronization
idempotent; changing reviewed content creates a new dataset identity. The local run files
remain the authoritative, checkpointed record.

The current runner is `make eval-run`; older experimental scripts under `evals/old/` and
`notebooks/` are not supported runtime paths.

The generator uses Pydantic-based structured responses and handles refusals following
the [official OpenAI structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs).
