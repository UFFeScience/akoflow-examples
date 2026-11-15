# OpenOil ensemble — 8 members

A real OpenDrift OpenOil oil-spill ensemble offshore of Maricá/Niterói, Brazil. This example has **8 independent simulation activities** and **14 native AkôFlow activities** in total. Each member produces NetCDF trajectories and a measured CPU/memory/runtime profile. Aggregation computes ensemble cell visitation, coast arrival, and oil fate; map, summary and animation activities produce the figures below. A terminal activity validates all scientific outputs and file checksums.

**Scientific limit:** the wind/current forcings are synthetic, constant in space/time, sampled between northeast wind and a cold-front regime. The coastline and OpenOil weathering calculations are real. This is a reproducible teaching experiment, **not an operational forecast**.

## Scenario

| Setting | Value |
| --- | --- |
| Members | 8 |
| Particles per member | 1,000 |
| Simulated duration | 172 h |
| Release | 16 h × 250 m³/h = 4,000 m³ |
| Start | 2026-11-20 06:00:00 (model clock; no timezone supplied in the notebook) |
| Location | longitude -42.90, latitude -23.25 |
| Oil | GENERIC MEDIUM CRUDE |
| Integration / output | 900 s / 1 h |
| Water temperature | 30 °C |
| Parameter seed / member seed | 42 / 42 + member index |
| Native execution lanes | 2 local Docker lanes |

The notebook introduction mentions 300 m³ and 72 h, but its executable configuration contains the values above. All three variants use nested parameter sampling: their shared member indices receive the same forcings and seeds. Complete production experiments run **serially on the homeserver: 8 → 16 → 32**, with validation before advancing. The 8- and 16-member runs use two explicit execution lanes; the 32-member run uses four lanes (four CPUs and 16 GiB of declared capacity). These different resource profiles must be considered when comparing observed durations.

## Run with Docker

The shared [Dockerfile](../../images/openoil/docker/Dockerfile), [locked dependencies](../../images/openoil/requirements.lock), [scientific runner](../../images/openoil/app/workflow.py), and [source notebook](../../images/openoil/source/openoil_derramamento_ensemble.ipynb) are versioned in this repository.

Published image: `ghcr.io/uffescience/openoil-ensemble:v1` for **linux/amd64 and linux/arm64**. The workflow and runner pin the tested multi-platform index digest rather than relying on a mutable tag. Both architectures pass the real offline small-ensemble check; full 8-member evidence records the homeserver amd64 execution.

```sh
./prepare.sh
./run.sh
./validate.sh
```

Preparation pulls the image. `run.sh` is a simple sequential standalone reproduction using the same stages with networking disabled; use the native AkôFlow workflow for the measured two-lane ensemble schedule. Keep enough memory for the OpenDrift coastline mask (roughly 2–3 GiB per member process) and disk for the complete NetCDF outputs. No cloud account, external API, live weather service, GPU or network connection is required during execution.

## Run through AkôFlow

From the repository root, configure `AKOFLOW_API_TOKEN` in your shell and set the daemon URL:

```sh
go run ./tools/daemon-local -root . -example scientific-workflows/openoil-ensemble-08 -api-url http://127.0.0.1:8080/akoflow-api -registry-image -lanes 2
```

Companion definitions: [workflow.yaml](workflow.yaml), [environment.yaml](environment.yaml), [scope.yaml](scope.yaml), and [topology.yaml](topology.yaml). Transfer edges explicitly name all required files. Imported execution plan predictions are placeholders and are not timing measurements. The profile CSV and native execution capture contain observed durations.

## Measured result gallery

![Actual 8-member probability map](figures/mapa_probabilidade.png)

![Actual 8-member mass balance, coast arrival and execution timeline](figures/resumo_workflow.png)

![Actual 8-member selected trajectory animation](figures/animacao.gif)

The GIF selects the member with the highest final stranded-particle fraction; ties select the first member. The map is the fraction of ensemble members with any recorded oil position in each grid cell. It is not a calibrated posterior probability.

## Result files and validation

The result archive contains every member's `.nc` trajectory, `probability.nc`, `arrival.csv`, `mass_balance.csv`, `summary.json`, `perfil_tarefas.csv`, per-stage profiles, PNGs, multi-frame GIF, selected-member trajectory and SHA-256 manifest. The profile CSV records member and aggregation measurements; the native capture also records rendering and validation activities.

The terminal validator checks particle/time dimensions, finite nonnegative mass, post-release mass conservation within 1%, probability bounds and exact hit-count normalization, decoded PNG dimensions and a GIF with multiple frames. Missing data or failed members abort the workflow; no precomputed or synthetic timing result substitutes for a failed simulation.

## Provenance

Adapted from the user-supplied `openoil_derramamento_ensemble.ipynb`; [provenance metadata](../../images/openoil/source/provenance.json) records its checksum. See [OpenDrift](https://github.com/OpenDrift/opendrift) for upstream code and licensing, [installation documentation](https://opendrift.github.io/install.html), and the dependency lock for scientific package versions. No real forcing-file integration is claimed as validated by these synthetic-forcing runs.
<!-- hub-publication -->

## Public Hub version and measured execution

[Open this workflow and its results](https://hub.akoflow.com/o/akoflow/scientific-workflows-openoil-ensemble-08) · [Documentation](https://akoflow.com/docs/showcase/scientific-workflows/openoil-ensemble-08)

### Import into AkôFlow Desktop

Create workflow → Import from Hub → paste this immutable URI:

```text
akoflow://hub/publications/0d02c2c1-da65-4a17-9919-a8cbcf703341/versions/1
```

The URI imports the workflow definition. Build or pull the public image and register the companion `environment.yaml`, `scope.yaml`, and `topology.yaml` from this source bundle before planning a local execution. No hosted account, GPU or cloud capacity is required for this CPU profile.

Image: `ghcr.io/uffescience/openoil-ensemble@sha256:267348059d11049d42458ab2e3a30cedb4efa143b619f60686d44525f1bba19a`.

### Actual homeserver results

Run `oilv1-openoil-ensemble-08-local-6f5ac4d22a-run-20261115t161927.919327106` completed **14/14** activities in **187.34679532051086 seconds**. These are measured Docker-backed computations, not simulated timing. The captured manual plan uses placeholder predicted timings; those predictions are not benchmark measurements. Use the observed execution metrics for performance analysis. Cost is the configured local compute cost and excludes electricity and hardware.

[Download the native experiment capture](https://hub.akoflow.com/api/v1/publications/0d02c2c1-da65-4a17-9919-a8cbcf703341/experiments/d20a815a-2c57-4a01-b774-4b7533421d41). The Hub Results tab includes the same plan, attempts, metrics and logs.

### Inputs and outputs

Input fixtures and scientific source are described in this bundle's README; inspect them together with the workflow definition and bundle configuration for profile assumptions. Fixtures are generated by the included code unless a bundle identifies an upstream dataset. No repository-wide LICENSE file is currently present: inspect the bundle and upstream terms before redistributing source or data; publication here does not grant additional rights. Outputs expected from this workflow:

- `scenario.json`
- `parameters.json`
- `probability.nc`
- `arrival.csv`
- `mass_balance.csv`
- `summary.json`
- `perfil_tarefas.csv`
- `selected-member.nc`
- `mapa_probabilidade.png`
- `resumo_workflow.png`
- `animacao.gif`
- `membro_000.nc`
- `membro_001.nc`
- `membro_002.nc`
- `membro_003.nc`
- `membro_004.nc`
- `membro_005.nc`
- `membro_006.nc`
- `membro_007.nc`
- `profile-member-000.json`
- `profile-member-001.json`
- `profile-member-002.json`
- `profile-member-003.json`
- `profile-member-004.json`
- `profile-member-005.json`
- `profile-member-006.json`
- `profile-member-007.json`
- `profile-prepare.json`
- `profile-aggregate.json`
- `profile-map.json`
- `profile-summary.json`
- `profile-animate.json`

[Download the actual validated output files](https://github.com/UFFeScience/akoflow-examples/releases/download/openoil-ensemble-v1/scientific-workflows-openoil-ensemble-08-results.tar.gz).
