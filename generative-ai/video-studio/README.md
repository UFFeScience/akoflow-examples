# AI Video Studio

Create a storyboard, procedural scene frames, generated narration audio, and a video from a versioned local brief. FFmpeg is used when available on the host; the supplied Docker image includes it. The portable fallback writes a valid YUV4MPEG stream rather than pretending to have produced an MP4.

## Run locally

Requires Go and Python 3.12+. Blender Render Farm also requires Docker. Run from a fresh checkout:

```sh
git clone https://github.com/UFFeScience/akoflow-examples.git
cd akoflow-examples/generative-ai/video-studio
./prepare.sh && ./run.sh
```

Preparation downloads the Go YAML module. Results are in `outputs/manifest.json`, `outputs/dag-validation.json`, and `outputs/stage-<activity>.json`. Independent branches run concurrently as soon as their own dependencies and a local execution slot are available.

## Inspect the same DAG in Desktop

Start the local AkôFlow daemon with Docker available and configure `AKOFLOW_API_TOKEN` in your shell. From this example directory:

```sh
go run ../../tools/daemon-local -root ../.. -example generative-ai/video-studio
```

The command builds the declared image, validates Docker connectivity, registers local-only infrastructure, and executes the workflow through the daemon. Current verified screenshots are in `screenshots/current/`; their manifest identifies the exact run and image. The full daemon projection is in `evidence/daemon-run.json`.
