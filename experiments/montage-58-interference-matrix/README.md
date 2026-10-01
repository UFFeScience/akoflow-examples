# Montage 58 interference calibration

This experiment measures the interference that the Montage `mProject` and
`mDiffFit` programs experience when they share one machine. It is a calibration
step for the later Montage 58 comparison across seven AkôFlow environments; it
does not execute the complete DAG.

Nothing in this directory runs automatically. Provisioning and measurements
require an explicit operator command.

## Fixed inputs

- OCI image: `ovvesley/akoflow-wf-montage@sha256:26b060b83b990557ea86ab40503cc8f17ab6016b5973e7e6f9201100a96440c9`
- Cloud machine: one GCP `e2-medium`, Ubuntu 24.04, 30 GiB balanced disk
- Per-process limit: one CPU and 1536 MiB
- Working directory: `/akoflow-wfa-shared` inside each container
- Repetitions: five, configurable with `REPETITIONS`

The source image contains the Montage binaries, FITS inputs and headers.
`docker/Dockerfile` derives a calibration image and materializes the two
projected FITS files required by `mDiffFit` during the image build. That build
is outside the measured window. Each measured container receives its own image
filesystem, so the test measures CPU, memory and host I/O contention without
allowing the two programs to overwrite one another's outputs.

## Matrix

| Case | Processes on the same machine | Purpose |
| --- | --- | --- |
| `mproject-a-alone` | `mProject A` | Baseline for the first projection |
| `mproject-b-alone` | `mProject B` | Baseline for the second projection |
| `mdifffit-alone` | `mDiffFit` | Baseline for the difference fit |
| `mproject-with-mproject` | `mProject A` + `mProject B` | Measure same-family interference |
| `mproject-with-mdifffit` | `mProject A` + `mDiffFit` | Measure cross-family interference |

The paired containers are created first and then started concurrently. Both are
pinned to the same host and limited to one CPU. Do not distribute a pair across
two VMs: that would remove the interference under study.

Run the cloud matrix before the local matrix. The runner pulls the source image
and builds the calibration image before recording either matrix; image transfer
and build time are excluded from activity duration.

## 1. Review the Terraform plan

```sh
cd experiments/montage-58-interference-matrix/terraform
terraform init
terraform plan \
  -var='project_id=YOUR_GCP_PROJECT' \
  -var='zone=us-central1-a' \
  -var='ssh_user=YOUR_LOGIN' \
  -var='ssh_public_key_path=/absolute/path/to/id_ed25519.pub' \
  -var='ssh_source_cidr=YOUR_PUBLIC_IP/32'
```

The requested work in this revision stops at the plan. Do **not** run
`terraform apply` until the experiment is approved.

## 2. Cloud execution procedure (not run yet)

After approval, apply the reviewed plan, wait for `docker-ready` in the serial
console, copy this directory to the VM and run:

```sh
REPETITIONS=5 ./scripts/run-matrix.sh cloud results/cloud
```

Copy `results/cloud/` back before destroying the VM. Then use
`terraform destroy` with the same variables. The Terraform state contains the
instance identity and must not be committed.

## 3. Local execution procedure (not run yet)

Use the same Docker engine that will represent the local AkôFlow environment:

```sh
REPETITIONS=5 ./scripts/run-matrix.sh local results/local
```

Do not run unrelated builds or containers during either matrix. Record the host
CPU, memory, operating system and Docker version beside the results.

## Result contract

Each result directory contains:

- `runs.tsv`: one row per process with case, repetition, workload, start/end,
  process duration, exit status and container identifier;
- `host.txt`: machine and Docker inventory;
- `logs/`: stdout/stderr for every process;
- `summary.tsv`: mean baseline and paired process durations plus slowdown ratios.

For each paired process calculate:

`slowdown = paired duration / matching isolated duration`

Report both process slowdowns, not only pair wall time. A slowdown above `1`
means the process became slower while sharing the machine. Keep all five raw
repetitions; use medians for the interference matrix and retain dispersion for
confidence intervals.

## Promotion to AkôFlow

Once cloud and local measurements are accepted, convert the median ratios into
environment-specific interference observations:

- `mProject → mProject`
- `mProject → mDiffFit`
- `mDiffFit → mProject`

The direction matters because cross-family effects need not be symmetric. The
calibrated values can then be registered for each of the seven environments and
used by PRISM when planning the full Montage 58 workflow.
