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

Showcase workflow documents declare an OCI image and a structured command for
each activity. They never invoke `docker run`: AkôFlow owns image delivery and
container startup for the selected runtime. The local `run.sh` fixture executes
the deterministic workload directly, while CI builds and validates the image as
a separate concern.

Product documentation is published at [akoflow.com](https://akoflow.com).

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
