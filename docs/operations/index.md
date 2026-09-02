# Operations

Running, shipping, and measuring the system.

- [Deployment](deployment.md) — local Docker Compose and the Azure multi-container pipeline.
- [Evaluation](evaluation.md) — RAGAS metrics and LangSmith datasets for the retriever.
- [Benchmarks](benchmarks.md) — Docling PDF parsing throughput on CPU versus GPU.

## Day-to-day commands

```bash
make compose            # bring the whole stack up
make redis-chat         # inspect a stored conversation
make create-eval-dataset
make run-evals
make lint && make test
```
