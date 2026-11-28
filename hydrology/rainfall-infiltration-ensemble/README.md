# Rainfall infiltration and ponding ensemble

This synthetic experiment implements the constant-rainfall, homogeneous-soil
setting described by Russell G. Mein and Curtis L. Larson in
[Modeling infiltration during a steady rain](https://doi.org/10.1029/WR009i002p00384)
(1973). The rainfall-limited phase ends at the analytic ponding time. After
ponding, fourth-order Runge–Kutta integration advances the Green–Ampt
equation. Independent bracketed inversion checks selected column results.

The ensemble uses 512 seeded batches, each with 256 synthetic soil columns.
Every storm runs for four hours on a two-minute sampling grid. Conductivity
varies by ±10% and suction by ±15% around each scenario's nominal value.
The [manifest audit](evidence/scenario-audit.json) records when ponding occurs.
The [pilot timings](evidence/pilot-timing.json) measure integration on selected
batches before daemon benchmarking.

The complete 514-activity DAG passed preflight on an isolated daemon with
per-report reuse of its shared recipe probe. The
[preflight comparison](evidence/preflight-comparison.json) records the
original timeout and the successful check with the image unmaterialized.

```sh
python3 scripts/scenarios.py
python3 scripts/run_batch.py 511 results
```

The AkôFlow driver resumes any completed four-slot reference execution and
runs three repetitions for each of the 1-, 4-, 8-, 16-, and 32-slot plans.
It checks the batch artifact inventory and the hashes of the aggregate CSV,
figure, and animation after each run.

```sh
python3 profile.py profile-evidence
```

## Four-slot reference

The AkôFlow run completed 514 activities, with four overlapping scientific
batches. The aggregate validated 512 batches and 131,072 columns. Of these,
77,729 columns reached ponding before the storm ended. The largest error against
bracketed inversion was 4.44 × 10⁻⁸ mm, rounded up.

![Runoff and infiltration in the reference run](evidence/reference/rainfall-runoff.png)

[Eight-frame rainfall–runoff animation](evidence/reference/rainfall-runoff.gif) ·
[Batch results CSV](evidence/reference/infiltration-batches.csv) ·
[Validation and artifact hashes](evidence/reference/reference-evidence.json)
