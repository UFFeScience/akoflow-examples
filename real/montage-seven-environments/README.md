# Montage 58 on seven real execution scopes

This campaign translates the seven historical simulation scenarios into real
AkôFlow execution scopes while preserving the PRISM Time placement selected for
each scenario. The workflow contains the original 58 Montage commands and a
deterministic duration for every activity, taken from the completed historical
run in `../montage-cloud-local/reference-runtimes.csv`.

The connected infrastructure is shared instead of duplicating credentials:

- Google Cloud project `fgcs-wesley-2026`, with public-catalog prices and
  `destroy-after-run` H3/C4D capacity targets;
- PlaFRIM through `ssh.plafrim.fr`, user `wferreir`, SLURM and Singularity;
- ten logical fog slots backed by the local AkôFlow Docker host.

The fog slots are concurrent execution lanes on one physical host. They are not
ten independent edge devices. Cross-site link values in `networks/` are
conservative static assumptions until an end-to-end measurement campaign
replaces them.

## Scenario mapping

| Scenario | Real resources |
| --- | --- |
| `cloud_hetero` | 2 × H3 standard, 1 × C4D standard, 1 × C4D high-memory |
| `cloud_homo` | 4 × C4D standard |
| `cluster_hetero` | 2 × PlaFRIM Bora, 2 × PlaFRIM Diablo |
| `cluster_homo` | 4 × PlaFRIM Bora |
| `hybrid_hetero` | 1 × Bora, 1 × Diablo, 1 × H3, 1 × C4D |
| `hybrid_homo` | 2 × Bora, 2 × C4D |
| `network_fog_hpc_cloud` | 10 × local fog lanes, 1 × Bora, 1 × Diablo, 1 × H3, 1 × C4D |

The historical planner modeled H4D resources. Real execution translates those
placements to the closest available shapes: `h4d-standard-192` becomes
`c4d-standard-192`, and `h4d-highmem-192` becomes `c4d-highmem-192`. Both keep
192 vCPUs and closely match memory capacity, but results must be identified as
C4D executions because CPU topology and network characteristics differ.

PlaFRIM no longer reports the historical `diablo01/02` nodes. The heterogeneous
cluster mapping uses the currently discovered `diablo03/04`, from the same
Diablo family. Resource availability is refreshed before a run; SLURM may queue
a job if a selected node changes state.

## Generated artifacts

- `workflow.json`: one definition supporting both real and simulated runs;
- `scopes/`: seven real execution scopes;
- `networks/`: one topology per scope;
- `plans/`: translated PRISM Time plans with 58 assignments each;
- `manifest.json`: IDs and resource inventory used by submission;
- `local-fog-environment.json`: local execution environment used only by the
  fog/HPC/cloud scenario.

Regenerate after the source planning campaign has been collected:

```sh
export AKOFLOW_API_TOKEN=...
ruby real/montage-seven-environments/generate.rb
```

Submit one scenario only after its environments are healthy:

```sh
real/montage-seven-environments/submit-run.sh \
  cluster_homo montage-real-cluster-homo-v1
```

Cloud runs can be expensive. At the catalog prices captured when this campaign
was prepared, four C4D standard instances cost about USD 35.52 per hour before
disk and network charges. Capacity targets create no VM by themselves; a real
run provisions on demand and destroys its instances after the run reaches a
terminal state.
