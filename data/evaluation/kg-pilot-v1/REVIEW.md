# KG pilot evaluation: source-review record

Prepared 2026-10-20 by Codex (AI source review; not astrophysicist validation).
Eight approved development questions: four single-paper controls, four cross-paper
comparisons. They are not eight claims that KG must beat Hybrid, nor a held-out test.

## What was checked

Each chosen record is approved, unquarantined and not dependency-held in the existing
expanded-v1 review. The existing KG validator checked that review against the authoritative
extraction checkpoints and plan. Original complete chunks—not graph summaries—were read
to verify the question, answer, conditions and uncertainty. Assembly additionally checks
that every quoted span is literally in its original chunk and that paper/build/version/
collection/source/page identities are inside the unchanged frozen evaluation scope.

The full 48-paper snapshot is reused, so the comparison does not make retrieval easier by
narrowing queries to graph papers. New reference passages are from existing full-text
artifacts in those frozen builds, not new indexing or PDF processing. The curated recipe
and individual review notes are in `curation.json` and
`evals/datasets/kg_pilot_v1.json`; exact selected KG record IDs and quotes are retained in
each question's `kg_reference`. Original KG decisions and old evaluation files are untouched.

| ID | Source pages | Review emphasis |
| --- | --- | --- |
| kg0001 | JWST survey p3 | M22 is explicitly NGC 6656; s-rich is about 0.2 dex more metal-rich; NGC 1851 differs. |
| kg0002 | Rubin binary study p4 | 2-degree initial query, 18-arcmin central exclusion, 10,136 parent objects before later membership filtering. |
| kg0003 | Omega Cen chemo-dynamics p7 | Shared rotation versus different anisotropy; 2.43-sigma and 0.51-sigma proxies are not equivalent detections. |
| kg0004 | SPURS p39 | Winds may deliver nitrogen enrichment; massive stars versus AGN remains unresolved. No quarantined velocity result used. |
| kg0005 | JWST p3; Tracing M22 p14 | Observed chemical differences versus unresolved AGB/SN-Ia and massive-star explanations. |
| kg0006 | Chemo-dynamics p7; bar-migration p1 | Internal population kinematics versus introductory stripped-nucleus/progenitor hypotheses. No invented causal link. |
| kg0007 | Rubin p4; axion study p24 | Applied crowding cut versus proposed nonuniform birthrate priors. Damaged birthrate numbers/units are not requested. |
| kg0008 | JWST p17; Rubin p12 | Future population measurements versus 0.87 precision/0.81 completeness at threshold 0.5. Neither metric is a binary fraction. |

## Limitations and interpretation

- AI review is not independent specialist peer review; source support may still need correction.
- These are comparisons and controls, not labelled multihop graph proofs. No new scientific
  relationships or object aliases were invented to make the graph appear more connected.
- Approved references in the graph do not guarantee runtime retrieval of those chunks.
  Inspect `graph_used_runs`, per-item graph diagnostics and selected evidence.
- References are one supported selection, not an exhaustive list of equivalent passages;
  low exact gold recall alone does not establish an incorrect answer.
- No approved unanswerable examples were added: an absence claim would need a separate
  frozen-corpus search, which this source review did not perform.
- All eight are development-only. Do not claim held-out or corpus-wide improvement from
  a small cohort deliberately selected for graph evidence coverage.

The assembler and format/source tests are free and offline. No paid benchmark was run.
See `docs/architecture/knowledge-graph.md` for validation and the explicit Hybrid/KG
benchmark command pinned to publication
`publication:ef340620c8c35358052b02616a177172a1bdc4710641fe603f2fc127b447ba70`.
