# Computer Vision

Generate seeded noisy 8×8 geometric-pattern images from the bundled input specification, validate labels, augment only training images, learn class centroids, and evaluate classification on held-out images. This small offline dataset is not CIFAR-10.

## Fresh local checkout

Requires Go and Python 3.12+. Run this command from the directory in which you keep your repositories:

```sh
git clone https://github.com/UFFeScience/akoflow-examples.git
cd akoflow-examples/machine-learning/computer-vision
./prepare.sh && ./run.sh
```

`prepare.sh` downloads the pinned Python packages (when required) and Go module once. `run.sh` then executes the local stages offline in dependency waves. Results are in `outputs/`; inspect `manifest.json`, `dag-validation.json`, and each `stage-<name>.json`. Independent branches run concurrently.

## Run

```sh
./run.sh
```

Requires Go and Python 3 for the standalone smoke test and Docker for execution through AkôFlow. The workflow graph is in [workflow.yaml](./workflow.yaml); the expected contract is in [expected/manifest.json](./expected/manifest.json).

Published image: `ghcr.io/uffescience/akoflow-examples/showcase-computer-vision:v1`.


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

[Open this workflow and its results](https://hub.akoflow.com/o/akoflow/machine-learning-computer-vision) · [Documentation](https://akoflow.com/docs/showcase/ai/machine-learning/computer-vision)

### Import into AkôFlow Desktop

Create workflow → Import from Hub → paste this immutable URI:

```text
akoflow://hub/publications/9c8d59e8-8d6d-4b67-8264-6b6951da921d/versions/1
```

The URI imports the workflow definition. Build or pull the public image and register the companion `environment.yaml`, `scope.yaml`, and `topology.yaml` from this source bundle before planning a local execution. No hosted account, GPU or cloud capacity is required for this CPU profile.

Image: `ghcr.io/uffescience/akoflow-examples/showcase-computer-vision@sha256:99eaa319fd1bf27cc989de0a211565bb8bad0d03e20e243467e4d0be1d84e250`.

### Actual homeserver results

Run `hubv1-showcase-computer-vision-local-9cab6f182c-run-20261115t054733.884301512` completed **6/6** activities in **41.27992582321167 seconds**. These are measured Docker-backed computations, not simulated timing. Cost is the configured local compute cost and excludes electricity and hardware.

[Download the native experiment capture](https://raw.githubusercontent.com/UFFeScience/akoflow-examples/AKO-238/machine-learning/computer-vision/evidence/experiment.json). The Hub Results tab includes the same plan, attempts, metrics and logs.

### Inputs and outputs

Input fixtures and their generation code are in this bundle's `data/` and `scripts/` directories; inspect them together with `data/input.json` for profile assumptions. Fixtures are generated by the included code unless a bundle identifies an upstream dataset. No repository-wide LICENSE file is currently present: inspect the bundle and upstream terms before redistributing source or data; publication here does not grant additional rights. Outputs expected from this workflow:

- `vision-metrics.json`
- `model.pkl`

[Download the actual validated output files](https://github.com/UFFeScience/akoflow-examples/releases/download/showcase-hub-v1/machine-learning-computer-vision-results.tar.gz).


### Illustrated walkthrough

The following reference screenshots come from the documentation walkthrough. The current measured run is recorded separately above.

#### augment

![augment](https://akoflow.com/showcase/evidence/machine-learning/computer-vision/augment.png)

#### collect-images

![collect-images](https://akoflow.com/showcase/evidence/machine-learning/computer-vision/collect-images.png)

#### evaluate

![evaluate](https://akoflow.com/showcase/evidence/machine-learning/computer-vision/evaluate.png)

#### import-labels

![import-labels](https://akoflow.com/showcase/evidence/machine-learning/computer-vision/import-labels.png)

#### package-model

![package-model](https://akoflow.com/showcase/evidence/machine-learning/computer-vision/package-model.png)

#### train-detector

![train-detector](https://akoflow.com/showcase/evidence/machine-learning/computer-vision/train-detector.png)

#### workflow

![workflow](https://akoflow.com/showcase/evidence/machine-learning/computer-vision/workflow.png)
