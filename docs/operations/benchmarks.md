# Benchmarks

## Docling PDF parsing

[Docling](https://github.com/docling-project/docling) gives far richer layout understanding
than a plain text extractor, at a significant compute cost. These measurements come from
`docling_trial/` and drive the decision about whether Docling can sit in the online ingestion
path or must stay in a batch job.

Two hardware configurations were compared:

- **CPU** — 11th Gen Intel® Core™ i7-1165G7 × 8 (Lenovo ThinkPad X1 Carbon Gen 9)
- **GPU** — Intel® Core™ i5-9600K × 6 with an NVIDIA RTX 3050

### [arXiv:2408.09869](https://arxiv.org/pdf/2408.09869) — 9 pages

| Hardware | Model init | Total conversion | Per page |
| --- | --- | --- | --- |
| i7-1165G7 (CPU) | 0.01 s | 92.80 s | **10.31 s** |
| i5-9600K + RTX 3050 | 0.00 s | 9.81 s | **1.09 s** |

### [arXiv:1502.04839](https://arxiv.org/pdf/1502.04839) — 8 pages

| Hardware | Model init | Total conversion | Per page |
| --- | --- | --- | --- |
| i7-1165G7 (CPU) | 0.00 s | 209.95 s | **26.24 s** |
| i5-9600K + RTX 3050 | 0.00 s | 13.59 s | **1.70 s** |

### Reading the numbers

- The RTX 3050 gives roughly a **9×** speed-up on the first paper and **15×** on the second.
- CPU cost varies enormously with document complexity — 10 s/page versus 26 s/page for two
  papers of similar length — while GPU cost stays close to 1–2 s/page. GPU throughput is not
  just faster, it is far more predictable.
- At 26 s/page on CPU, a 300-page corpus is over two hours of parsing. That is why bulk
  ingestion goes through the [batch path](../architecture/ingestion.md#smart-batching) rather
  than blocking an upload request.

Reproduce with `docling_trial/trying_docling.py`; raw output is in `docling_trial/Benchmark.txt`.
