# Inference Benchmark

Measure actual local CPU inference with three batching profiles and verify identical predictions. The branches named CPU, GPU, and edge use CPU fallback batching in the portable profile; no GPU/edge hardware performance or cloud billing is claimed.

## Fresh local checkout

Requires Go and Python 3.12+. Run this command from the directory in which you keep your repositories:

```sh
git clone https://github.com/UFFeScience/akoflow-examples.git
cd akoflow-examples/machine-learning/inference-benchmark
./prepare.sh && ./run.sh
```

`prepare.sh` downloads the pinned Python packages (when required) and Go module once. `run.sh` then executes the local stages offline in dependency waves. Results are in `outputs/`; inspect `manifest.json`, `dag-validation.json`, and each `stage-<name>.json`. Independent branches run concurrently.

## Run

```sh
./run.sh
```

Requires Go and Python 3 for the standalone smoke test and Docker for execution through AkôFlow. The workflow graph is in [workflow.yaml](https://github.com/UFFeScience/akoflow-examples/blob/726301d112f7728d178da21695b2c12f2bc258f2/machine-learning/inference-benchmark/workflow.yaml); the expected contract is in [expected/manifest.json](https://github.com/UFFeScience/akoflow-examples/blob/726301d112f7728d178da21695b2c12f2bc258f2/machine-learning/inference-benchmark/expected/manifest.json).

Published image: `ghcr.io/uffescience/akoflow-examples/showcase-inference-benchmark:v1`.


## Run locally step by step

### 1. Check the prerequisites

Install Go, Python 3, Docker, and a local AkôFlow server/Desktop. Set the local API connection, then confirm every prerequisite:

```sh
export AKOFLOW_API_URL=http://127.0.0.1:8080/akoflow-api
export AKOFLOW_API_TOKEN=akoflow-development-token

python3 --version
docker version
curl --fail -H "Authorization: Bearer $AKOFLOW_API_TOKEN" "$AKOFLOW_API_URL/health/"
```

### 2. Run the deterministic smoke test

From this showcase directory:

```sh
./run.sh
```

The command recreates `outputs/`, launches one process per activity in dependency waves (siblings run concurrently), and validates every artifact declared in `expected/manifest.json`.

### 3. Build the image used by the workflow

```sh
IMAGE=$(sed -n 's/^[[:space:]]*image: //p' workflow.yaml | head -n 1)
docker build -f docker/Dockerfile -t "$IMAGE" .
```

The workflow command is authoritative. The image intentionally has no competing `ENTRYPOINT`.

### 4. Register the local infrastructure and workflow

```sh
for item in "environments environment.yaml" "execution-scopes scope.yaml" "network-topologies topology.yaml" "workflow-definitions workflow.yaml"
do
  set -- $item
  curl --fail-with-body -H "Authorization: Bearer $AKOFLOW_API_TOKEN" -H 'Content-Type: application/yaml' --data-binary "@$2" "$AKOFLOW_API_URL/$1/"
done
```

The order matters: the execution scope references the environment version, the topology references the scope, and the workflow references its namespaced local runtime.

### 5. Plan and execute in AkôFlow Desktop

1. Open **Workflows → Definitions** and select this showcase.
2. Choose **Generate plan**.
3. Select the execution scope imported from `scope.yaml`.
4. Run **HEFT** and select its feasible candidate.
5. Choose **Execute plan** and confirm **Real execution**.
6. Wait until the run is `completed` and every activity is settled.

### 6. Verify the result

Open the completed run and inspect:

- **Activities** for the engine-rendered DAG and per-activity status;
- **Workflow** for the observed execution lifecycle and timing decomposition;
- **Data** for workspace transfers;
- the final activity's **Generated files** table for file names, sizes, and SHA-256 checksums.

Historical captures are stored in `screenshots/`. They predate the corrected DAG and must not be used to verify this revision. The measured execution and validated outputs for this publication are recorded below. Current local evidence is `outputs/dag-validation.json` plus `outputs/stage-<activity>.json`.

Historical capture names:

- `workflow.png`: completed activity DAG;
- `execution.png`: observed execution lifecycle and timing decomposition;
- `outputs.png`: data transfers between activity workspaces;
- `generated-files.png`: files observed in the final output-producing activity.
<!-- hub-publication -->

## Public Hub version and measured execution

[Open this workflow and its results](https://hub.akoflow.com/o/akoflow/machine-learning-inference-benchmark) · [Documentation](https://akoflow.com/docs/showcase/ai/machine-learning/inference-benchmark)

### Import into AkôFlow Desktop

Create workflow → Import from Hub → paste this immutable URI:

```text
akoflow://hub/publications/a0dde05c-5f4e-425a-94b7-6c6436e3cee7/versions/1
```

The URI imports the workflow definition. Build or pull the public image and register the companion `environment.yaml`, `scope.yaml`, and `topology.yaml` from this source bundle before planning a local execution. No hosted account, GPU or cloud capacity is required for this CPU profile.

Image: `ghcr.io/uffescience/akoflow-examples/showcase-inference-benchmark@sha256:f9f193b68631f9098c72cc3334a0a7d577c41e195772ee9e933b17b8b9598cf2`.

### Actual homeserver results

Run `hubv1-showcase-inference-benchmark-local-e776bfef04-run-20261115t054830.960361831` completed **6/6** activities in **14.700184345245361 seconds**. These are measured Docker-backed computations, not simulated timing. The captured manual plan uses placeholder predicted timings; those predictions are not benchmark measurements. Use the observed execution metrics for performance analysis. Cost is the configured local compute cost and excludes electricity and hardware.

[Download the native experiment capture](https://hub.akoflow.com/api/v1/publications/a0dde05c-5f4e-425a-94b7-6c6436e3cee7/experiments/46692b46-a9b1-4fbb-832f-bf161120a9e6). The Hub Results tab includes the same plan, attempts, metrics and logs.

### Inputs and outputs

Input fixtures and their generation code are in this bundle's `data/` and `scripts/` directories; inspect them together with the workflow definition and bundle configuration for profile assumptions. Fixtures are generated by the included code unless a bundle identifies an upstream dataset. No repository-wide LICENSE file is currently present: inspect the bundle and upstream terms before redistributing source or data; publication here does not grant additional rights. Outputs expected from this workflow:

- `benchmark.csv`
- `report.html`

[Download the actual validated output files](https://github.com/UFFeScience/akoflow-examples/releases/download/showcase-hub-v1/machine-learning-inference-benchmark-results.tar.gz).


### Illustrated walkthrough

The following reference screenshots come from the documentation walkthrough. The current measured run is recorded separately above.

#### compare-cost-and-latency

![compare-cost-and-latency](https://akoflow.com/showcase/evidence/machine-learning/inference-benchmark/compare-cost-and-latency.png)

#### cpu

![cpu](https://akoflow.com/showcase/evidence/machine-learning/inference-benchmark/cpu.png)

#### edge

![edge](https://akoflow.com/showcase/evidence/machine-learning/inference-benchmark/edge.png)

#### freeze-inputs

![freeze-inputs](https://akoflow.com/showcase/evidence/machine-learning/inference-benchmark/freeze-inputs.png)

#### gpu

![gpu](https://akoflow.com/showcase/evidence/machine-learning/inference-benchmark/gpu.png)

#### normalize

![normalize](https://akoflow.com/showcase/evidence/machine-learning/inference-benchmark/normalize.png)

#### workflow

![workflow](https://akoflow.com/showcase/evidence/machine-learning/inference-benchmark/workflow.png)
