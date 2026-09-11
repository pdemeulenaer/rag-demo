# Evaluation

## Generate a first question set

From the repository root, with PostgreSQL and Qdrant reachable using your host `.env`:

```bash
make eval-preview             # Freeze evidence and show the plan; NO model calls
make create-eval-dataset      # Paid OpenAI generation from that saved preview
```

The default samples up to **50 active arXiv papers**, four text excerpts per paper,
and plans **50 candidates**: 30 single-paper, 15 cross-paper comparisons, and 5
insufficient-evidence cases. It uses `gpt-4.1-mini` and your `OPENAI_API_KEY`.
Neither command changes PostgreSQL/Qdrant, ingests papers, or publishes to LangSmith.
No RAGAS, Groq, Cohere or LangSmith credentials are needed for generation.

Look in `data/evaluation/star-clusters/`:

- `snapshot.json`: sampled text, titles, page numbers when available, collection/point
  IDs, paper/version/build identity and the active-corpus fingerprint.
- `plan.json`: frozen question types, evidence groups, prompt, model and limits.
- `results.json`: submission journal, saved background response IDs/statuses and terminal
  outputs, plus completed candidates/rejections and token usage.
- `questions.json`: candidate questions, reference answers, source excerpts, exact
  supporting quotes and `review_status: needs_review`.

The snapshot is a **sample of indexed text**, not a full corpus backup. Preview respects
the configured arXiv category/topic scope and embedding model, so its paper count may
be lower than `make papers-count` (which includes uploads and all ready builds).
It reads only manifest-listed points belonging to active builds, excludes figures and
generated summaries, and fails on missing points or identity drift. Legacy upload
adoption relies on its observed manifest. Use `make papers-audit` for vector validation.

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

Cross-paper partners are chosen by title/abstract word overlap without embeddings.
This is a simple starting heuristic, not a knowledge graph or a guarantee of meaningful
scientific overlap. Unsupported pairs can be skipped; duplicate questions, unknown
evidence IDs, non-verbatim quotes and invalid paper counts are rejected. Thus **50
planned questions can yield fewer than 50 candidates**. Inspect the rejection entries.

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

All generated answers are **synthetic drafts, not verified ground truth**. Exact quote
validation proves that quoted text exists, not that the answer follows from it.

1. Verify every answer against the excerpts and original paper; correct units, conditions
   and scientific claims. Reject trivial, ambiguous or near-duplicate questions.
2. Check that cross-paper questions genuinely require both papers. A citation to each
   paper alone does not prove a multi-step reasoning requirement.
3. Treat `unanswerable_candidate` as unanswerable **only in the supplied excerpts**.
   Search the full frozen corpus before accepting it as a corpus-level abstention test.
   Its reference evidence is empty; its generation evidence remains in the snapshot.
4. In a separate reviewed copy, mark accepted records `review_status: approved` and
   rejected records `rejected`. Add a few real questions of your own to reduce synthetic bias.
5. Separate development and held-out test papers **before tuning**; connected cross-paper
   groups must stay in one split. Keep the same approved questions and corpus when
   comparing Vanilla, Hybrid and future graph/agentic modes.

The generator does not run benchmarks or implement dataset splitting. A mode-aware
evaluation runner consuming this reviewed local format is the next milestone. Daily
ingestion can change the live corpus; the fingerprint detects changes but does not pin
historical query serving. Retain the snapshot and use a controlled corpus for comparisons.

## Legacy evaluation scripts

`evals/eval_dataset_creation.py` is the old upload-only generator with automatic LangSmith
publication; **the Make target no longer invokes it**. Existing datasets are untouched.

`make run-evals` still runs `evals/eval_retriever.py`, the legacy LangSmith/RAGAS evaluator.
It uses a separately named remote dataset and does **not** consume the new `questions.json`
or compare explicit Vanilla/Hybrid presets. Do not use it as the new benchmark yet.
It requires external services and evaluation dependencies. Earlier experiments remain
in `evals/old/` and `notebooks/`.

The generator uses Pydantic-based structured responses and handles refusals following
the [official OpenAI structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs).
