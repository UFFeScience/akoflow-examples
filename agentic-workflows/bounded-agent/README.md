# Bounded Agent

A reproducible AkôFlow showcase. It executes a real Docker image locally, writes deterministic artifacts, validates its output contract, and includes three versioned screenshots captured from a completed AkôFlow engine run.

## Run

```sh
./run.sh
```

Requires Docker, Node.js, and a Playwright-compatible Chromium installation (the screenshot command provisions it when needed). The workflow graph is in [workflow.yaml](./workflow.yaml); the expected contract is in [expected/manifest.json](./expected/manifest.json).

Published image: `ghcr.io/uffescience/akoflow-showcase-bounded-agent:v1`.

