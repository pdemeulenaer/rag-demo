# Operations

Running, shipping, and measuring the system.

- [Deployment](deployment.md) — local Docker Compose and the Azure multi-container pipeline.
- [Evaluation](evaluation.md) — reviewed, frozen-corpus Vanilla/Hybrid benchmarks.
- [Observability](observability.md) — repo-owned Langfuse stack, traces and Dataset Experiments.
- [Benchmarks](benchmarks.md) — Docling PDF parsing throughput on CPU versus GPU.

## Day-to-day commands

```bash
make compose            # bring the whole stack up
make langfuse-up        # start the optional repo-owned observability stack
make redis-chat         # inspect a stored conversation
make create-eval-dataset
make eval-run EVAL_DIR=data/evaluation/markdown-mini-v1 EVAL_LIMIT=2
make lint && make test
```
