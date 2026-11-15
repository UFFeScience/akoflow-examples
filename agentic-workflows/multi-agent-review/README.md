# Multi-Agent Review

Run three independent local reviewer programs in parallel: statistical review, independent numeric recomputation, and domain-bound checks. A critic checks agreement and accepts or corrects a supplied mean before the synthesis is published. The reviewers are deterministic programs rather than hosted LLM agents.

## Fresh local checkout

Requires Go and Python 3.12+. Run this command from the directory in which you keep your repositories:

```sh
git clone https://github.com/UFFeScience/akoflow-examples.git
cd akoflow-examples/agentic-workflows/multi-agent-review
./prepare.sh && ./run.sh
```

`prepare.sh` downloads the pinned Python packages (when required) and Go module once. `run.sh` then executes the local stages offline in dependency waves. Results are in `outputs/`; inspect `manifest.json`, `dag-validation.json`, and each `stage-<name>.json`. Independent branches run concurrently.

## Run

```sh
./run.sh
```

Requires Go and Python 3 for the standalone smoke test and Docker for execution through AkôFlow. The workflow graph is in [workflow.yaml](https://github.com/UFFeScience/akoflow-examples/blob/726301d112f7728d178da21695b2c12f2bc258f2/agentic-workflows/multi-agent-review/workflow.yaml); the expected contract is in [expected/manifest.json](https://github.com/UFFeScience/akoflow-examples/blob/726301d112f7728d178da21695b2c12f2bc258f2/agentic-workflows/multi-agent-review/expected/manifest.json).

Published image: `ghcr.io/uffescience/akoflow-examples/showcase-multi-agent-review:v1`.


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

[Open this workflow and its results](https://hub.akoflow.com/o/akoflow/agentic-workflows-multi-agent-review) · [Documentation](https://akoflow.com/docs/showcase/ai/agentic-workflows/multi-agent-review)

### Import into AkôFlow Desktop

Create workflow → Import from Hub → paste this immutable URI:

```text
akoflow://hub/publications/1bed32d8-cf60-487b-b4d3-663aed054202/versions/1
```

The URI imports the workflow definition. Build or pull the public image and register the companion `environment.yaml`, `scope.yaml`, and `topology.yaml` from this source bundle before planning a local execution. No hosted account, GPU or cloud capacity is required for this CPU profile.

Image: `ghcr.io/uffescience/akoflow-examples/showcase-multi-agent-review@sha256:f0ead4436917c972c907260066abfe47d17311dfc4dbef5e716861390dedbfb6`.

### Actual homeserver results

Run `hubv1-showcase-multi-agent-review-local-42e085614f-run-20261115t055417.277695740` completed **7/7** activities in **15.758075714111328 seconds**. These are measured Docker-backed computations, not simulated timing. The captured manual plan uses placeholder predicted timings; those predictions are not benchmark measurements. Use the observed execution metrics for performance analysis. Cost is the configured local compute cost and excludes electricity and hardware.

[Download the native experiment capture](https://hub.akoflow.com/api/v1/publications/1bed32d8-cf60-487b-b4d3-663aed054202/experiments/d3c0c08d-a36d-481d-a8e2-a3fe67f6e1df). The Hub Results tab includes the same plan, attempts, metrics and logs.

### Inputs and outputs

Input fixtures and their generation code are in this bundle's `data/` and `scripts/` directories; inspect them together with the workflow definition and bundle configuration for profile assumptions. Fixtures are generated by the included code unless a bundle identifies an upstream dataset. No repository-wide LICENSE file is currently present: inspect the bundle and upstream terms before redistributing source or data; publication here does not grant additional rights. Outputs expected from this workflow:

- `synthesis.md`
- `review.json`

[Download the actual validated output files](https://github.com/UFFeScience/akoflow-examples/releases/download/showcase-hub-v1/agentic-workflows-multi-agent-review-results.tar.gz).


### Illustrated walkthrough

The following reference screenshots come from the documentation walkthrough. The current measured run is recorded separately above.

#### code

![code](https://akoflow.com/showcase/evidence/agentic-workflows/multi-agent-review/code.png)

#### critic-review

![critic-review](https://akoflow.com/showcase/evidence/agentic-workflows/multi-agent-review/critic-review.png)

#### domain

![domain](https://akoflow.com/showcase/evidence/agentic-workflows/multi-agent-review/domain.png)

#### publish-evidence

![publish-evidence](https://akoflow.com/showcase/evidence/agentic-workflows/multi-agent-review/publish-evidence.png)

#### research

![research](https://akoflow.com/showcase/evidence/agentic-workflows/multi-agent-review/research.png)

#### shared-context

![shared-context](https://akoflow.com/showcase/evidence/agentic-workflows/multi-agent-review/shared-context.png)

#### synthesize

![synthesize](https://akoflow.com/showcase/evidence/agentic-workflows/multi-agent-review/synthesize.png)

#### workflow

![workflow](https://akoflow.com/showcase/evidence/agentic-workflows/multi-agent-review/workflow.png)
