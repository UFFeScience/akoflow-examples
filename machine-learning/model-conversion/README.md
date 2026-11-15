# Model Conversion

Export a learned affine model as real ONNX and TorchScript files, generate int8 and IEEE float16 coefficient representations in parallel, reload both executable formats, and compare their numeric outputs against the original model. The float16 branch runs on CPU and does not build or claim a TensorRT engine.

## Fresh local checkout

Requires Go and Python 3.12+. Run this command from the directory in which you keep your repositories:

```sh
git clone https://github.com/UFFeScience/akoflow-examples.git
cd akoflow-examples/machine-learning/model-conversion
./prepare.sh && ./run.sh
```

`prepare.sh` downloads the pinned Python packages (when required) and Go module once. `run.sh` then executes the local stages offline in dependency waves. Results are in `outputs/`; inspect `manifest.json`, `dag-validation.json`, and each `stage-<name>.json`. Independent branches run concurrently.

## Run

```sh
./run.sh
```

Requires Go and Python 3 for the standalone smoke test and Docker for execution through AkôFlow. The workflow graph is in [workflow.yaml](./workflow.yaml); the expected contract is in [expected/manifest.json](./expected/manifest.json).

Published image: `ghcr.io/uffescience/akoflow-examples/showcase-model-conversion:v1`.


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

Historical captures are stored in `screenshots/`. They predate the corrected DAG and must not be used to verify this revision. New daemon execution and one capture per activity are still required before claiming Desktop verification. Current local evidence is `outputs/dag-validation.json` plus `outputs/stage-<activity>.json`.

Historical capture names:

- `workflow.png`: completed activity DAG;
- `execution.png`: observed execution lifecycle and timing decomposition;
- `outputs.png`: data transfers between activity workspaces;
- `generated-files.png`: files observed in the final output-producing activity.

## Current execution evidence

The current completed daemon run is recorded in `evidence/daemon-run.json`. One capture for every activity and the observed DAG are in `screenshots/current/`; `capture-manifest.json` identifies their exact run and image. Older captures directly under `screenshots/` are historical and do not verify this revision.

<!-- hub-publication -->

## Public Hub version and measured execution

[Open this workflow and its results](https://hub.akoflow.com/o/akoflow/machine-learning-model-conversion) · [Documentation](https://akoflow.com/docs/showcase/ai/machine-learning/model-conversion)

### Import into AkôFlow Desktop

Create workflow → Import from Hub → paste this immutable URI:

```text
akoflow://hub/publications/0b26ad29-87a9-457e-bc7c-d81ae79d451f/versions/1
```

The URI imports the workflow definition. Build or pull the public image and register the companion `environment.yaml`, `scope.yaml`, and `topology.yaml` from this source bundle before planning a local execution. No hosted account, GPU or cloud capacity is required for this CPU profile.

Image: `ghcr.io/uffescience/akoflow-examples/showcase-model-conversion@sha256:e6790b9d51ea0a10d6bddbf43211c49dec1b19f436fbbcbaf7ad66f04598e720`.

### Actual homeserver results

Run `hubv1-showcase-model-conversion-local-6f2c213241-run-20261115t055000.623474610` completed **7/7** activities in **15.081406354904175 seconds**. These are measured Docker-backed computations, not simulated timing. Cost is the configured local compute cost and excludes electricity and hardware.

[Download the native experiment capture](https://raw.githubusercontent.com/UFFeScience/akoflow-examples/AKO-238/machine-learning/model-conversion/evidence/experiment.json). The Hub Results tab includes the same plan, attempts, metrics and logs.

### Inputs and outputs

Input fixtures and their generation code are in this bundle's `data/` and `scripts/` directories; inspect them together with `data/input.json` for profile assumptions. Fixtures are generated by the included code unless a bundle identifies an upstream dataset. No repository-wide LICENSE file is currently present: inspect the bundle and upstream terms before redistributing source or data; publication here does not grant additional rights. Outputs expected from this workflow:

- `model.onnx`
- `model.torchscript.pt`
- `model-int8.json`
- `model-fp16.bin`
- `validation.json`

[Download the actual validated output files](https://github.com/UFFeScience/akoflow-examples/releases/download/showcase-hub-v1/machine-learning-model-conversion-results.tar.gz).


### Illustrated walkthrough

The following reference screenshots come from the documentation walkthrough. The current measured run is recorded separately above.

#### export-onnx

![export-onnx](https://akoflow.com/showcase/evidence/machine-learning/model-conversion/export-onnx.png)

#### export-torchscript

![export-torchscript](https://akoflow.com/showcase/evidence/machine-learning/model-conversion/export-torchscript.png)

#### load-model

![load-model](https://akoflow.com/showcase/evidence/machine-learning/model-conversion/load-model.png)

#### publish-variants

![publish-variants](https://akoflow.com/showcase/evidence/machine-learning/model-conversion/publish-variants.png)

#### quantize-cpu

![quantize-cpu](https://akoflow.com/showcase/evidence/machine-learning/model-conversion/quantize-cpu.png)

#### quantize-gpu

![quantize-gpu](https://akoflow.com/showcase/evidence/machine-learning/model-conversion/quantize-gpu.png)

#### validate-outputs

![validate-outputs](https://akoflow.com/showcase/evidence/machine-learning/model-conversion/validate-outputs.png)

#### workflow

![workflow](https://akoflow.com/showcase/evidence/machine-learning/model-conversion/workflow.png)
