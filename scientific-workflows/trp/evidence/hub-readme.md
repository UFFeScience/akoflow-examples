# TRP — TCGA-BRCA microRNA networks

Six-stage Transparent Reproducible Pipeline from [BSB 2025](https://doi.org/10.5753/bsb.2025.15126), evaluated with real GDC observations and current miRWalk exports. [Original implementation v0.1.0](https://github.com/LIS-Unicamp/pan-cancer-analysis/tree/v0.1.0), commit `914e8f0b60a8ec5c7df2cedf73b482c183b9aa2b`. [Implementation and execution tracking](https://github.com/UFFeScience/akoflow-examples/issues/44).

## Execution history and versions

The six scientific stages completed across two native daemon executions. This publication preserves both runs without changing their recorded status:

- **Version 1:** complete six-stage workflow definition and the original native execution. Metadata access, metadata filtering, expression aggregation and edgeR filtering completed. The strict transport stopped stage five when miRWalk explicitly returned no matching ID.
- **Version 2:** two-stage checkpoint continuation, containing interaction inference and network construction. Both activities completed successfully. The remaining four scientific stages are inherited from the earlier execution through a verified checkpoint, rather than reported as new activities in this run.

The continuation verified 1,932 checkpoint files against original native artifact SHA-256 observations, reusing four completed stages and 396 already verified downloads. The final archive retains six scientific stage records and continuation provenance.

## Scientific inputs and measured results

- 488 selected cases from the paper cohort.
- 1,084 GDC observations, 2,474,865,141 bytes, downloaded by original UUID and verified against vendor MD5 and size.
- All 436 expressed-miRNA queries accounted for: 433 real miRWalk CSV exports and three exact no-match HTML responses, preserved with SHA-256 receipts. The same three accessions are unmapped upstream: MIMAT0017985, MIMAT0018073 and MIMAT0032110. No empty interaction CSV was fabricated.
- All five groups evaluated 41,169 candidate miRNA–mRNA pairs each.

| Group | Interaction edges | Association edges |
| --- | ---: | ---: |
| basal-like | 296 | 13 |
| her2-enriched | 13 | 0 |
| luminal-a | 259 | 11 |
| luminal-b | 584 | 32 |
| normal | 5072 | 48 |

Independent checks passed for raw metadata hashes, GDC/miRWalk acquisition coverage, finite and bounded Spearman/FDR statistics, unrounded interaction thresholds, network node closure, every Jaccard association and association threshold membership. The final three artifacts match the daemon's sealed SHA-256/size manifest. All retained miRWalk CSV and no-match snapshot hashes were checked again after collection.

Post-computation comparison matched all 20 expression aggregates, both expressed-molecule tables and all 30 network tables with the source release after label/row alignment. Expression rtol/atol: 1e-12. Network rtol: 1e-10; atol: 1e-12. Reference outputs were used only for comparison after calculation, never as scientific execution inputs.

## Reproduction scope

Stage one validates and stages the release's four frozen raw metadata/supplementary inputs; it does not claim to rerun live cohort-metadata requests. The remaining scientific notebook cells and thresholds are unchanged, with bounded and checked transport replacing browser/download orchestration. Runtime: Python 3.12.16, exact upstream Python requirements and edgeR 3.40.2. The article describes edgeR 4; observed numerical agreement does not imply an identical historical environment.

This Hub publication uploads workflow definitions and native execution evidence, including logs, metrics, events and file references. It does not upload datasets, the result archive, notebook source or Docker image binaries. Referenced `akoflow-local/trp` images and `/app/scripts` belong to the measured local installation; importing the definition alone does not install that runtime. The two-stage continuation additionally requires its retained local checkpoint. Use the full six-stage definition for a fresh execution after provisioning its companion runtime.
