# Blender Render Farm

Build a real Blender scene, render even and odd frames in parallel using Cycles on the CPU, compose an MP4, and verify all six frames. The default command uses Docker, so the host does not need a Blender installation. No JSON file is represented as a .blend file.

## Run locally

Requires Go and Python 3.12+. Blender Render Farm also requires Docker. Run from a fresh checkout:

```sh
git clone https://github.com/UFFeScience/akoflow-examples.git
cd akoflow-examples/rendering/blender-render-farm
./prepare.sh && ./run.sh
```

Preparation downloads the Go YAML module. Results are in `outputs/manifest.json`, `outputs/dag-validation.json`, and `outputs/stage-<activity>.json`. Independent branches run concurrently as soon as their own dependencies and a local execution slot are available.

## Inspect the same DAG in Desktop

Start the local AkôFlow daemon with Docker available and configure `AKOFLOW_API_TOKEN` in your shell. From this example directory:

```sh
go run ../../tools/daemon-local -root ../.. -example rendering/blender-render-farm
```

The command builds the declared image, validates Docker connectivity, registers local-only infrastructure, and executes the workflow through the daemon. Current verified screenshots are in `screenshots/current/`; their manifest identifies the exact run and image. The full daemon projection is in `evidence/daemon-run.json`.
