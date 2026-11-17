# TRP — TCGA-BRCA microRNA networks

Run all six scientific stages from [BSB 2025](https://doi.org/10.5753/bsb.2025.15126) with real GDC observations and miRWalk exports. This package includes the Dockerfile, original notebooks/configuration, exact upstream Python requirements, four verified raw metadata inputs, acquisition adapters, native AkôFlow definitions, local runner and validators. It starts from metadata and does not require a checkpoint or any file from the author's execution machine.

[Tracking item AKO-44](https://github.com/UFFeScience/akoflow-examples/issues/44) · [Hub publication](https://hub.akoflow.com/u/ovvesley/trp-tcga-brca) · [Original scientific source v0.1.0](https://github.com/LIS-Unicamp/pan-cancer-analysis/tree/v0.1.0)

## Build and run locally

Requirements: Docker Engine/Desktop and Python 3. Linux amd64 is the tested execution platform; other CPU architectures require Docker's amd64 emulation. Start with 16 GiB available RAM and 40 GiB available scratch storage. A complete run downloads about 2.5 GB of GDC observations plus several GB of miRWalk data and can take tens of minutes. GDC and miRWalk must be reachable from Docker.

From the repository root:

```sh
cd scientific-workflows/trp
./prepare.sh
./run.sh
```

The same commands work inside the standalone source package; Go and a running AkôFlow daemon are not needed for this Docker reproduction. `prepare.sh` builds the image from the supplied Dockerfile and validates its six notebook sources, raw input hashes and Python/R dependencies. `run.sh` executes every stage, in order, and validates the final artifacts. It preserves existing results and refuses to overwrite a populated output directory.

To pull the released public image instead of building:

```sh
./prepare.sh --pull
./run.sh
```

`image.lock.json` records the public immutable image reference once released. To use another empty output directory:

```sh
./run.sh --output /absolute/path/to/new-results
./validate.sh --output /absolute/path/to/new-results
```

To build explicitly with Docker, from this bundle directory:

```sh
docker build --platform linux/amd64 -f docker/Dockerfile -t akoflow-local/trp:workload .
TRP_IMAGE=akoflow-local/trp:workload ./run.sh --output /absolute/path/to/new-results
```

Use `./prepare.sh` for a recorded, checked preparation. For an explicitly selected prebuilt image, set `TRP_IMAGE` to its immutable OCI reference when invoking the runner. `./validate.sh -definition` checks the image/contract without claiming a full scientific run.

## Execute through AkôFlow and monitor in Desktop

Import `workflow.yaml`, register `environment.yaml`, `scope.yaml` and `topology.yaml`, then create a plan and run it. The workflow's six activities reference the public GHCR image and exchange their declared stage archives through native data dependencies. The environment uses local Docker and provisions no cloud machines.

With this repository's daemon helper and Go installed:

```sh
go run ../../tools/daemon-local -root ../.. -example scientific-workflows/trp \
  -api-url http://127.0.0.1:8080/akoflow-api -registry-image -build=false -wait=false
```

Provide `AKOFLOW_API_TOKEN` through the installation's protected environment or pass `-env-file /absolute/path/to/protected.env`. Use the actual daemon address when it does not bind to loopback. The command prints the run ID and records `evidence/daemon-run.json`. Observe the same submitted run with `-observe`; do not submit duplicates when observation times out. Desktop uses the registered native workflow and plan, not the standalone runner.

The CPU/RAM values in the native environment are scheduling declarations. Current local Docker execution does not enforce cgroup CPU/memory limits; the numerical libraries use one BLAS thread and joblib uses at most two workers.

## Stages and scientific scope

1. Validate and stage four frozen raw metadata/supplementary inputs from the upstream release. This preserves the paper cohort and does not claim to requery live cohort metadata.
2. Execute original metadata filtering: 488 selected cases and 1,084 GDC file UUIDs.
3. Download original observations, verify vendor MD5/size and retain SHA-256 receipts; execute original expression processing/aggregation for all five groups.
4. Execute original edgeR molecule-expression filtering.
5. Acquire miRWalk CSV tables and execute the original filters, Spearman correlations and FDR correction.
6. Execute original interaction/association network construction and independently validate the computed results.

Groups: basal-like, HER2-enriched, luminal A, luminal B and normal tissue. No patient subsampling and no author-computed expression/network results are used as scientific inputs. Only transport is adapted. A successful miRWalk page with the exact `No ID matched your search criteria` marker is preserved as HTML with a SHA-256 receipt; it does not generate an empty interaction CSV. Unknown responses, HTTP errors and invalid downloads stop execution. The original browser implementation also leaves these no-match queries unmapped.

GDC raw per-file observations are discarded only after successful aggregation; UUID, vendor MD5, length and SHA-256 receipts remain. Raw miRWalk CSVs remain in the final archive because the service has no immutable snapshot identifier. The result may change when public databases change.

## Outputs and validation

`outputs/` contains `stage-06.tar.gz`, `scientific-validation.json`, `network-summary.png` and per-stage observations. The final archive retains all five groups' computed expression, inference, interaction/association network tables, raw miRWalk snapshots, input/transport receipts and six stage records.

Validation independently checks input hashes and coverage, finite/bounded statistics, unrounded correlation/FDR selection thresholds, interaction-node closure, every Jaccard association, association threshold membership, and retained miRWalk CSV/no-match snapshot hashes. A successful process exit alone is insufficient.

The prior six-stage scientific result, completed through a checkpoint continuation, matched all 20 aggregate tables, both expression-flag tables and all 30 network tables against the source release after computation. See `evidence/aggregation-expression-comparison.json` and `evidence/network-comparison.json` for tolerances. Historical Hub v1/v2 retain the original interruption and continuation; their machine-specific images/checkpoint are historical evidence, not prerequisites for this fresh six-stage package.

## Toolchain and attribution

Source commit: `914e8f0b60a8ec5c7df2cedf73b482c183b9aa2b`. Python base image is pinned by OCI digest; Python requirements match upstream; Debian edgeR is fixed to 3.40.2. The article describes edgeR 4, so observed numerical agreement is not an assertion of an identical historical environment. See [THIRD_PARTY.md](THIRD_PARTY.md) and `data/provenance.json` for scientific attribution, upstream notices and input hashes.
