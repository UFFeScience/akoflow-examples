# AkôFlow examples

Runnable workflows, infrastructure fixtures, showcase assets, and experiment
tooling for [AkôFlow](https://github.com/UFFeScience/akoflow).

The AkôFlow engine repository contains the runtime and product documentation.
This repository owns executable examples so their dependencies, generated
assets, and validation workflows can evolve independently from the engine.

## Repository layout

- `simulation/`, `local/`, `kind/`, `slurm/`, and `real/`: execution and
  infrastructure examples.
- `machine-learning/`, `generative-ai/`, `agentic-workflows/`, and
  `scientific-ai/`: complete showcase workflows.
- `connections/`, `onboarding/`, and `server-instance/`: reusable connection
  and installation templates.
- `experiments/`: Python and Node.js tools used to launch, collect, analyze,
  and render reproducible scheduling experiments.

Each directory documents its prerequisites. Run a showcase fixture from its
own directory with `./run.sh`. Most API-driven examples expect an AkôFlow
daemon at `http://localhost:8080` and accept the usual AkôFlow environment
variables for endpoint and token overrides.

Product documentation is published at [akoflow.com](https://akoflow.com).
