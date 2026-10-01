# Runnable showcase standard

New end-to-end showcases must be reproducible workloads, not timing simulations.
They follow this contract:

1. **Correct domain ownership.** Store the example under its technical domain
   (`generative-ai`, `document-ai`, `media`, `rendering`, and so on), never a
   marketing category.
2. **Offline execution.** `run.sh` must complete without network access. Small
   fixtures belong in `data/`; large public datasets may have an explicit
   preparation script, checksum, license note, and deterministic local fallback.
3. **Observable stages.** Each meaningful computation is a separate AkôFlow
   activity. Parallel work is expressed with `dependsOn`, and activities exchange
   artifacts only through the execution workspace.
4. **Real computation.** Stages process data with the declared toolchain. Do not
   use `sleep` or precomputed outputs to imitate work.
5. **Portable smoke profile.** The default run is CPU-compatible and small enough
   for CI. `AKOFLOW_PROFILE=demo`, `standard`, or `stress` may increase dataset
   size, frame count, model size, or repetitions without changing the DAG.
6. **Stable result contract.** A successful run writes `outputs/manifest.json`
   with `showcase`, `status`, and `artifacts`. `validate.sh` checks semantics and
   non-empty artifacts, not only process exit status.
7. **Container parity.** `docker/Dockerfile` contains every runtime dependency and
   invokes the same stage runner used by `run.sh`.
8. **Complete AkôFlow inputs.** Every showcase includes `workflow.yaml`,
   `environment.yaml`, `scope.yaml`, and `topology.yaml` plus a concise README.
9. **Safe optional integrations.** Hosted APIs, Ollama, GPU acceleration, and
   external storage are opt-in adapters. Secrets never appear in fixtures,
   commands, logs, or committed output.

The five reference implementations are AI Video Studio, Document Intelligence,
Local RAG Factory, Video Intelligence, and Blender Render Farm.

