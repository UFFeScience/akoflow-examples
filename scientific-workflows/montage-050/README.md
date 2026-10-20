# Montage 050 locally

Run all 58 original Montage 050d activities locally, using the immutable amd64 image and its twelve bundled FITS observations. The default uses two CPU slots, preserves the 138 named file handoffs, creates three calibrated astronomical mosaics and a color preview, and provisions no cloud machines. This is a long-running scientific workload; on Apple Silicon Docker uses amd64 emulation.

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
