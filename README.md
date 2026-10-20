# AkôFlow examples

Local runnable examples for [AkôFlow](https://github.com/UFFeScience/akoflow), with the same activity DAGs used in Desktop and in the project documentation.

The catalog contains 27 small CPU workloads and the full 58-activity Montage 050d scientific workflow. Each example includes its input data (or a pinned image carrying that data), a preparation command, a local runner, a validator, and local daemon infrastructure. Current Desktop captures are in each bundle's `screenshots/current/`, with their exact run and image identified in its manifest.

## Clone once and run a local example

Install Go and Python 3.12+. Blender and Montage also require Docker; Montage requires linux/amd64 support. Preparation downloads the Go YAML module and the pinned packages required by that example. Workloads then run on local input data. The small examples perform real computation; their teaching profiles do not require cloud credentials, hosted LLMs, or GPU hardware.

```sh
git clone https://github.com/UFFeScience/akoflow-examples.git
cd akoflow-examples
```

Each command below starts from the repository root and keeps your shell in that directory:

| Example | Local command (from the repository root) |
| --- | --- |
| [Montage 050 locally](scientific-workflows/montage-050/README.md) | `(cd scientific-workflows/montage-050 && ./prepare.sh && ./run.sh)` |
| [AI Assisted Analysis](scientific-ai/ai-assisted-analysis/README.md) | `(cd scientific-ai/ai-assisted-analysis && ./prepare.sh && ./run.sh)` |
| [Experiment Feedback Loop](scientific-ai/experiment-feedback-loop/README.md) | `(cd scientific-ai/experiment-feedback-loop && ./prepare.sh && ./run.sh)` |
| [Surrogate Model](scientific-ai/surrogate-model/README.md) | `(cd scientific-ai/surrogate-model && ./prepare.sh && ./run.sh)` |
| [Anomaly Detection](machine-learning/anomaly-detection/README.md) | `(cd machine-learning/anomaly-detection && ./prepare.sh && ./run.sh)` |
| [Batch Inference](machine-learning/batch-inference/README.md) | `(cd machine-learning/batch-inference && ./prepare.sh && ./run.sh)` |
| [Computer Vision](machine-learning/computer-vision/README.md) | `(cd machine-learning/computer-vision && ./prepare.sh && ./run.sh)` |
| [Hyperparameter Search](machine-learning/hyperparameter-search/README.md) | `(cd machine-learning/hyperparameter-search && ./prepare.sh && ./run.sh)` |
| [Inference Benchmark](machine-learning/inference-benchmark/README.md) | `(cd machine-learning/inference-benchmark && ./prepare.sh && ./run.sh)` |
| [Infrastructure Selection](machine-learning/infrastructure-selection/README.md) | `(cd machine-learning/infrastructure-selection && ./prepare.sh && ./run.sh)` |
| [LoRA Fine Tuning](machine-learning/lora-fine-tuning/README.md) | `(cd machine-learning/lora-fine-tuning && ./prepare.sh && ./run.sh)` |
| [Model Comparison](machine-learning/model-comparison/README.md) | `(cd machine-learning/model-comparison && ./prepare.sh && ./run.sh)` |
| [Model Conversion](machine-learning/model-conversion/README.md) | `(cd machine-learning/model-conversion && ./prepare.sh && ./run.sh)` |
| [Model Distillation](machine-learning/model-distillation/README.md) | `(cd machine-learning/model-distillation && ./prepare.sh && ./run.sh)` |
| [Model Ensemble](machine-learning/model-ensemble/README.md) | `(cd machine-learning/model-ensemble && ./prepare.sh && ./run.sh)` |
| [Training with MLflow](machine-learning/training-with-mlflow/README.md) | `(cd machine-learning/training-with-mlflow && ./prepare.sh && ./run.sh)` |
| [Audio Transcription](generative-ai/audio-transcription/README.md) | `(cd generative-ai/audio-transcription && ./prepare.sh && ./run.sh)` |
| [Document Extraction](generative-ai/document-extraction/README.md) | `(cd generative-ai/document-extraction && ./prepare.sh && ./run.sh)` |
| [Local RAG Factory](generative-ai/local-rag/README.md) | `(cd generative-ai/local-rag && ./prepare.sh && ./run.sh)` |
| [RAG Indexing](generative-ai/rag-indexing/README.md) | `(cd generative-ai/rag-indexing && ./prepare.sh && ./run.sh)` |
| [Synthetic Dataset](generative-ai/synthetic-dataset/README.md) | `(cd generative-ai/synthetic-dataset && ./prepare.sh && ./run.sh)` |
| [AI Video Studio](generative-ai/video-studio/README.md) | `(cd generative-ai/video-studio && ./prepare.sh && ./run.sh)` |
| [Bounded Agent](agentic-workflows/bounded-agent/README.md) | `(cd agentic-workflows/bounded-agent && ./prepare.sh && ./run.sh)` |
| [Multi-Agent Review](agentic-workflows/multi-agent-review/README.md) | `(cd agentic-workflows/multi-agent-review && ./prepare.sh && ./run.sh)` |
| [Supervised Tool Loop](agentic-workflows/supervised-tool-loop/README.md) | `(cd agentic-workflows/supervised-tool-loop && ./prepare.sh && ./run.sh)` |
| [Document Intelligence](document-ai/document-intelligence/README.md) | `(cd document-ai/document-intelligence && ./prepare.sh && ./run.sh)` |
| [Video Intelligence](media/video-intelligence/README.md) | `(cd media/video-intelligence && ./prepare.sh && ./run.sh)` |
| [Blender Render Farm](rendering/blender-render-farm/README.md) | `(cd rendering/blender-render-farm && ./prepare.sh && ./run.sh)` |

The standalone command writes `outputs/manifest.json`, `outputs/dag-validation.json`, and `outputs/stage-<activity>.json`. Independent activities become ready after their own dependencies complete; the local runner enforces a bounded number of concurrent processes. A failed stage prevents a successful final manifest.

## Run the same DAG through the daemon

Start a local AkôFlow daemon with Docker available and configure `AKOFLOW_API_TOKEN` in your shell. For example:

```sh
go run ./tools/daemon-local -example machine-learning/training-with-mlflow
```

This validates Docker through the daemon API, builds the declared OCI image, registers local-only infrastructure and the workflow, imports a plan, and submits a real run. The daemon performs execution and artifact transfers; the renderer never runs connectivity checks, shell commands, or Docker. The command records the exact projection in `evidence/daemon-run.json` and prints the run ID for inspection in Desktop.

For the full long-running scientific example, submit and leave the daemon in charge:

```sh
go run ./tools/daemon-local -example scientific-workflows/montage-050 -wait=false
```

## Workload scope

The local profiles are explicit about their inputs and algorithms. They include numerical integration and regression, a tiny rank-one adapter, geometric image classification, real ONNX and TorchScript export, schema-based generation, a tone-vocabulary audio recognizer, pixel-template OCR, and bounded deterministic tool agents. Infrastructure comparisons separate CPU measurements from declared placement assumptions. The MLflow example uses the actual SDK and a local SQLite tracking store.

Montage preserves all 58 original native commands and 138 named file handoffs from the pinned 050d image. It is not a timing simulation and can take substantially longer than the small profiles. Its CI preparation check verifies the source and image contract without claiming full mosaic completion.

## Repository layout

- `scientific-workflows/` and `scientific-ai/`: astronomical mosaics, numerical experiments, and learned scientific surrogates.
- `machine-learning/`, `generative-ai/`, `document-ai/`, `media/`, `rendering/`, and `agentic-workflows/`: local domain examples.
- `workloads/`: canonical implementations for the 22 small pattern workloads; `go run ./tools/materialize` generates their standalone source bundles.
- `tools/`: Go runners, catalog discovery, infrastructure generation, documentation export, and validators.
- `simulation/`, `local/`, `kind/`, `slurm/`, `real/`, `connections/`, `onboarding/`, `server-instance/`, and `experiments/`: additional infrastructure and experiment bundles.

The [showcase standard](SHOWCASE_STANDARD.md) defines offline workload execution, real computation, observable activities, and artifact validation. Product documentation is published at [akoflow.com](https://akoflow.com).

## Continuous integration

The example files live in this repository, while the reusable CI implementation
is maintained in `UFFeScience/akoflow/.github/workflows/examples-ci.yml`. The
small workflow in this repository passes the exact pull-request or `main`
commit to that central workflow. Runnable showcases are discovered from their
`docker/Dockerfile` and executable `run.sh`; adding a showcase does not require
editing a duplicated matrix.

After a push to `main`, CI publishes validated showcase images to GHCR and
notifies the AkôFlow documentation workflow. Configure the repository secret
`AKOFLOW_DOCS_DISPATCH_TOKEN` with access to dispatch workflows in
`UFFeScience/akoflow`. If the secret is temporarily unavailable, the daily
documentation reconciliation still checks out this repository and validates
all referenced example files.
