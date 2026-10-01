# Montage-6448: fixed interference and progressive PRISM knowledge

This experiment complements the original 90-run interference campaign. The
original campaign changed the percentage of activities that actually suffered
interference. This campaign keeps execution interference fixed and changes only
what PRISM knows while planning.

## Research questions

1. How much prediction error and makespan regret does PRISM incur with no
   interference knowledge?
2. How quickly do PRISM Time and PRISM Cost converge toward the full-knowledge
   oracle as knowledge coverage increases?
3. At which knowledge coverage does each PRISM objective equal or outperform
   HEFT in observed makespan, observed cost, feasibility, or Pareto dominance?
4. Does partial knowledge change placement stability, concurrent overlap, and
   resource usage before it materially changes makespan?
5. Is knowledge more valuable for time optimization or cost optimization in a
   heterogeneous hybrid environment?

## Controlled design

| Factor | Values |
| --- | --- |
| Workflow | Montage, 6,448 activities and 18,924 dependencies |
| Environment | `scheduler-hybrid_hetero-v1` |
| Execution interference truth | 100% of Montage activities, slowdown 1.5 |
| PRISM knowledge coverage | 0%, 10%, 20%, 50%, 80%, 100% |
| Seeds | 1, 2, 3, 4, 5 |
| Algorithms | PRISM Time, PRISM Cost, HEFT |
| Sessions | 30 |
| Simulations | 90 |

Coverage prefixes are nested for each seed. A 20% snapshot contains every
activity known at 10% for the same seed. The execution truth does not change
between coverage levels. HEFT is intentionally repeated as a negative control:
its results should not depend on PRISM's knowledge snapshot.

`interferenceMatrix` is the execution truth stored on the selected plan and
consumed by SimGrid. `interferenceKnowledgeMatrix` is the partial snapshot used
only by PRISM during planning. At 0%, PRISM is blind but execution still suffers
the full slowdown. At 100%, PRISM receives the oracle matrix.

## Frozen environment

The environment reproduces the original hybrid heterogeneous model:

| Resource | Cores | Memory | Speedup | Price/s | Boot |
| --- | ---: | ---: | ---: | ---: | ---: |
| PlaFRIM `bora011` | 36 | 192 GiB | 7.09 | 0 | 0 s |
| PlaFRIM `diablo03` | 64 | 256 GiB | 5.68 | 0 | 0 s |
| GCP `h3-standard-88-2` | 88 | 352 GiB | 20.00 | 0.0013676667 | 12 s |
| GCP `h4d-standard-192-7` | 192 | 720 GiB | 39.27 | 0.0021816 | 12 s |

Cluster-to-cluster and cloud-to-cloud links use 750 Mbit/s. Cross-boundary
links use 500 Mbit/s. Cloud-to-cloud traffic costs USD 0.01/GiB, represented as
`1e-11` per byte to match the original protocol.

## Sources and provenance

The Google Drive file `AkoFlow/FGCS/akoflow.db` currently has size zero both in
Drive metadata and on disk, so it is not treated as evidence. The reproducible
inputs are instead the checked experiment outputs and the normalized workflow
snapshot preserved by the former scheduler repository:

- workflow snapshot: `build/akoflow-validation-minus20/montage-6448/hybrid_hetero/workflow-definition.json`;
- workflow SHA-256: `e68e7fbc6a590162c467710562a6963a8305b3b6559ec10fc0a141275ce25202`;
- source WfCommons instance: `montage-chameleon-dss-20d-001`;
- original completed campaign: `outputs/prism-paper-experiments/interference-campaign-r2-manifest.json` and `interference-simulation-r2-results.json.gz`;
- SLA reference: HEFT makespan `15988.20233395195 s`, cost `34.87986221174968`;
- factor 1.2 limits: deadline `19185.84280074234 s`, budget `41.85583465409962`.

## Prepare the clean AkôFlow database

Start the current AkôFlow server, point `AKOFLOW_API_URL` and
`AKOFLOW_API_TOKEN` to it, then run:

```sh
examples/simulation/montage-6448-interference-knowledge/bootstrap.sh
```

The script imports only the workflow, environment, scope, and topology. It does
not start planning or simulation.

Generate and inspect the campaign manifest:

```sh
python3 scripts/experiments/create_interference_knowledge_campaign.py \
  --campaign-prefix interference-knowledge-r1-1790460000 \
  --thresholds outputs/prism-paper-experiments/sla-thresholds.json \
  --output outputs/prism-paper-experiments/interference-knowledge-r1-manifest.json
```

Add `--submit` only after reviewing the manifest. Planning and simulations use
the existing campaign launch and collection scripts.

## Primary outcomes

For each algorithm, seed, and knowledge coverage, report:

- predicted and observed makespan and cost;
- absolute and relative prediction error;
- deadline and budget feasibility;
- accumulated interference time;
- number of activities and activity families moved between resources relative
  to 0% and 100%;
- resource active time, utilization, and cloud share;
- regret against the same-seed 100% PRISM oracle;
- dominance against HEFT and the oracle Pareto frontier.

Use paired comparisons within each seed. Report the median, interquartile range,
and all five seed values rather than treating the 90 runs as independent
replicates. The acceptance control is that HEFT remains invariant across
knowledge coverage for the same seed; a variation indicates an uncontrolled
input or nondeterminism.

## Follow-up: online learning

This campaign is a controlled knowledge ablation, not yet an estimator. A
second campaign can learn the matrix from completed execution evidence. Its
snapshots should be recorded after 0, 1, 2, 4, 8, and 16 prior runs, then frozen
before planning the next held-out run. The measured slowdown must come from
overlapping activities on the same resource; a clean first run supplies base
runtimes but cannot by itself estimate interference. This follow-up should only
start after the fixed-truth campaign validates the causal effect of knowledge.
