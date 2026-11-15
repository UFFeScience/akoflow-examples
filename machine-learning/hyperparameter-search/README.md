# Hyperparameter Search

Train three independent gradient-descent regressors with different learning rates and epoch budgets, rank their measured held-out errors, and publish the best learned model and leaderboard.

## Fresh local checkout

Requires Go and Python 3.12+. Run this command from the directory in which you keep your repositories:

```sh
git clone https://github.com/UFFeScience/akoflow-examples.git
cd akoflow-examples/machine-learning/hyperparameter-search
./prepare.sh && ./run.sh
```

`prepare.sh` downloads the pinned Python packages (when required) and Go module once. `run.sh` then executes the local stages offline in dependency waves. Results are in `outputs/`; inspect `manifest.json`, `dag-validation.json`, and each `stage-<name>.json`. Independent branches run concurrently.

## Run

```sh
./run.sh
```

Requires Go and Python 3 for the standalone smoke test and Docker for execution through AkôFlow. The workflow graph is in [workflow.yaml](./workflow.yaml); the expected contract is in [expected/manifest.json](./expected/manifest.json).

Published image: `ghcr.io/uffescience/akoflow-examples/showcase-hyperparameter-search:v1`.


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

[Open this workflow and its results](https://hub.akoflow.com/o/akoflow/machine-learning-hyperparameter-search) · [Documentation](https://akoflow.com/docs/showcase/ai/machine-learning/hyperparameter-search)

### Import into AkôFlow Desktop

Create workflow → Import from Hub → paste this immutable URI:

```text
akoflow://hub/publications/12f30a7f-d58d-43e5-9a90-eba31de75a9e/versions/1
```

The URI imports the workflow definition. Build or pull the public image and register the companion `environment.yaml`, `scope.yaml`, and `topology.yaml` from this source bundle before planning a local execution. No hosted account, GPU or cloud capacity is required for this CPU profile.

Image: `ghcr.io/uffescience/akoflow-examples/showcase-hyperparameter-search@sha256:638cc469c08fcb393648551ecc6454edc44f4506565636bd2c017989d2334f41`.

### Actual homeserver results

Run `showcase-hyperparameter-search-local-14e6b92f12-run-20261115t053132.291109559` completed **6/6** activities in **15.873935461044312 seconds**. These are measured Docker-backed computations, not simulated timing. Cost is the configured local compute cost and excludes electricity and hardware.

[Download the native experiment capture](https://raw.githubusercontent.com/UFFeScience/akoflow-examples/AKO-238/machine-learning/hyperparameter-search/evidence/experiment.json). The Hub Results tab includes the same plan, attempts, metrics and logs.

### Inputs and outputs

Input fixtures and their generation code are in this bundle's `data/` and `scripts/` directories; inspect them together with `data/input.json` for profile assumptions. Source code and fixtures follow the repository license unless a bundle states an upstream data license. Outputs expected from this workflow:

- `leaderboard.csv`
- `best-model.pkl`

### Illustrated walkthrough

The following reference screenshots come from the documentation walkthrough. The current measured run is recorded separately above.

#### compare-trials

![compare-trials](https://akoflow.com/showcase/evidence/machine-learning/hyperparameter-search/compare-trials.png)

#### prepare-dataset

![prepare-dataset](https://akoflow.com/showcase/evidence/machine-learning/hyperparameter-search/prepare-dataset.png)

#### register-best

![register-best](https://akoflow.com/showcase/evidence/machine-learning/hyperparameter-search/register-best.png)

#### trial-1

![trial-1](https://akoflow.com/showcase/evidence/machine-learning/hyperparameter-search/trial-1.png)

#### trial-2

![trial-2](https://akoflow.com/showcase/evidence/machine-learning/hyperparameter-search/trial-2.png)

#### trial-n

![trial-n](https://akoflow.com/showcase/evidence/machine-learning/hyperparameter-search/trial-n.png)

#### workflow

![workflow](https://akoflow.com/showcase/evidence/machine-learning/hyperparameter-search/workflow.png)

