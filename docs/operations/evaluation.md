# Evaluation

Evaluation lives in `evals/` and combines [RAGAS](https://docs.ragas.io) metrics with
LangSmith datasets.

## Building a dataset

```bash
make create-eval-dataset      # uv run python evals/eval_dataset_creation.py
```

This generates question/context pairs from the ingested corpus and uploads them as a
LangSmith dataset.

## Running the evaluation

```bash
make run-evals                # uv run python evals/eval_retriever.py
```

`eval_retriever.py` sets `EVALUATION_MODE=true` before importing the pipeline, which changes
its behaviour in one important way:

!!! note "Evaluation mode"
    With `EVALUATION_MODE=true`, `rag_pipeline` retrieves `top_k=5` and **skips Cohere
    reranking**, and `get_memory` returns a fresh `ConversationMemory` on every call. This
    isolates retrieval quality from reranking and from conversational carry-over.

## Metrics

The evaluation wraps LangChain LLM and embedding clients in RAGAS adapters and scores each
sample with:

| Metric | What it measures |
| --- | --- |
| `Faithfulness` | Is the answer grounded in the retrieved context? |
| `ResponseRelevancy` | Does the answer address the question? |
| `LLMContextPrecisionWithoutReference` | Are the retrieved chunks relevant? |
| `LLMContextRecall` | Was the needed context retrieved, judged by an LLM? |
| `NonLLMContextRecall` | The same, judged against reference contexts |

Older experiments — a RAGAS-for-LangChain variant and standalone LangSmith scripts — are kept
under `evals/old/` for reference.

## Notebooks

`notebooks/` holds the exploratory work behind these evaluations: preprocessing,
dataset creation, hybrid search experiments, and RAGAS runs.
