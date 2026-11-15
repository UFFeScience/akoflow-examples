# Montage 050 — Astronomical Image Mosaicking

Run all 58 original Montage 050d activities locally, using the immutable amd64 image and its twelve bundled FITS observations. The default uses two CPU slots, preserves the 138 named file handoffs, creates three calibrated astronomical mosaics and a color preview, and provisions no cloud machines. This is a long-running scientific workload; on Apple Silicon Docker uses amd64 emulation.

## Execution profiles

### Local Docker — executed and validated

The published reference run completed **58/58 activities** on the homeserver with two CPU slots. It produced three validated 1800×1800 FITS mosaics and four PNG previews. The immutable workflow URI and measured execution capture on this page refer to this profile. Configure [workflow.yaml](workflow.yaml), [environment.yaml](environment.yaml), [scope.yaml](scope.yaml) and [topology.yaml](topology.yaml) from the source bundle. On Apple Silicon, Docker requires amd64 emulation.

### GCP + local processing — configuration reference, not executed in this validation

The same 58-activity computation can use the [GCP/local deployment bundle](../../real/montage-cloud-local/README.md): twelve projection activities are assigned to four GCP workers and the remaining processing runs locally. This requires your own cloud account, credentials, quota, networking and cleanup. **No new GCP run or GCP timing/cost result is claimed.** Historical predicted values are configuration references, not measurements of the validated local run.

The previous separate Montage GCP/local publication has been consolidated here. It reused the identical local execution; it was not a second experiment. Its immutable definitions remain available for compatibility: [historical GCP YAML](https://hub.akoflow.com/api/v1/publications/bae34aba-fbc6-423f-8921-6e4dc5ea5d4a/versions/1/yaml). The [GCP deployment guide](https://akoflow.com/docs/showcase/montage-cloud-local/) describes that optional profile.

## Run locally

Install Go and Docker with linux/amd64 support. Keep at least 15 GiB of free disk for the image and intermediate workspaces; the exact peak depends on artifact retention and concurrency. The image already contains the 87 MiB input dataset, headers, tables, and Montage executables.

```sh
git clone https://github.com/UFFeScience/akoflow-examples.git
cd akoflow-examples/scientific-workflows/montage-050
./prepare.sh && ./run.sh
```

Preparation downloads the Go YAML module and the pinned image. Activities run with network access disabled. The local runner copies the image's input seed once, executes native Montage commands as soon as their dependencies and a CPU slot are available, and publishes a successful manifest only after every activity and final file passes validation. No activity is replaced with a simulation or omitted.

Outputs are in `outputs/`: three FITS mosaics, three monochrome previews, the color preview, per-activity observations, and a manifest with SHA-256 digests. The validator checks FITS image dimensions and decodes the PNG headers.

## Run through the local daemon and Desktop

With your local AkôFlow daemon running and `AKOFLOW_API_TOKEN` configured in the shell, run from this bundle:

```sh
go run ../../tools/daemon-local -root ../.. -example scientific-workflows/montage-050 -wait=false
```

This builds the same pinned image, validates the daemon's Docker connection, registers a local-only environment and the full 58-activity DAG, and submits a real run. It prints the run ID and leaves the daemon responsible for execution. Open that run in Desktop to inspect progress or cancel it. The local environment allows two simultaneous activities. No GCP credentials, VMs, Kubernetes cluster, or remote HPC account are used.

## Provenance

Derived from `real/montage-cloud-local/workflow.json`. The native commands, twelve source FITS files, 58 activity names, dependency graph, and 138 file handoffs are preserved. Historical `simulation.durationSeconds` values in the source describe a different CPU; they are planning references, not measurements of this local run. The immutable upstream image is:

```text
ovvesley/akoflow-wf-montage@sha256:26b060b83b990557ea86ab40503cc8f17ab6016b5973e7e6f9201100a96440c9
```

<!-- hub-publication -->

## Public Hub version and measured execution

[Open this workflow and its results](https://hub.akoflow.com/o/akoflow/scientific-workflows-montage-050) · [Documentation](https://akoflow.com/docs/showcase/scientific-workflows/montage-050)

### Import into AkôFlow Desktop

Create workflow → Import from Hub → paste this immutable URI:

```text
akoflow://hub/publications/4a1b3c21-a122-4c19-bd2d-c305d400b41f/versions/1
```

The URI imports the workflow definition. Build or pull the public image and register the companion `environment.yaml`, `scope.yaml`, and `topology.yaml` from this source bundle before planning a local execution. No hosted account, GPU or cloud capacity is required for this CPU profile.

Image: `ghcr.io/uffescience/akoflow-examples/montage-050-local@sha256:26b060b83b990557ea86ab40503cc8f17ab6016b5973e7e6f9201100a96440c9`.

### Actual homeserver results

Run `montage-050-local-local-79df14ee2e-run-20261115t052715.750879194` completed **58/58** activities in **3196.8059842586517 seconds**. These are measured Docker-backed computations, not simulated timing. The captured manual plan uses placeholder predicted timings; those predictions are not benchmark measurements. Use the observed execution metrics for performance analysis. Cost is the configured local compute cost and excludes electricity and hardware.

[Download the native experiment capture](https://hub.akoflow.com/api/v1/publications/4a1b3c21-a122-4c19-bd2d-c305d400b41f/experiments/4932099c-030e-47c5-acff-0ac0a32611e1). The Hub Results tab includes the same plan, attempts, metrics and logs.

### Inputs and outputs

Input fixtures and their generation code are in this bundle's `data/` and `scripts/` directories; inspect them together with the workflow definition and bundle configuration for profile assumptions. Fixtures are generated by the included code unless a bundle identifies an upstream dataset. No repository-wide LICENSE file is currently present: inspect the bundle and upstream terms before redistributing source or data; publication here does not grant additional rights. Outputs expected from this workflow:

- `1-mosaic.fits`
- `2-mosaic.fits`
- `3-mosaic.fits`
- `1-mosaic.png`
- `2-mosaic.png`
- `3-mosaic.png`
- `mosaic-color.png`

[Download the actual validated output files](https://github.com/UFFeScience/akoflow-examples/releases/download/showcase-hub-v1/scientific-workflows-montage-050-results.tar.gz).


### Images from this validated execution

![1-mosaic.png](https://akoflow.com/showcase/results/montage-050/1-mosaic.png)

![2-mosaic.png](https://akoflow.com/showcase/results/montage-050/2-mosaic.png)

![3-mosaic.png](https://akoflow.com/showcase/results/montage-050/3-mosaic.png)

![mosaic-color.png](https://akoflow.com/showcase/results/montage-050/mosaic-color.png)


### Illustrated walkthrough

The following reference screenshots come from the documentation walkthrough. The current measured run is recorded separately above.

#### workflow

![workflow](https://akoflow.com/showcase/evidence/scientific-workflows/montage-050/workflow.png)


The captured run used local alias `ghcr.io/uffescience/akoflow-examples/montage-050-local:local-5781d026f51ba438`. Its complete filesystem layers, runtime configuration, OS and architecture were compared with the public digest above and match; the recorded capture preserves the original image reference.
