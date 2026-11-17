#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "${1:-}" = "-definition" ]; then
  exec docker run --rm --network none --mount "type=bind,src=$root/workflow.yaml,dst=/app/workflow.yaml,readonly" --entrypoint python3 akoflow-local/opendronemap:workload /app/scripts/validate_definition.py
fi
python3 "$root/scripts/verify_hashes.py" "$root/outputs"
docker run --rm --network none --user "$(id -u):$(id -g)" --env HOME=/tmp --mount "type=bind,src=$root/outputs,dst=/outputs,readonly" --entrypoint python3 akoflow-local/opendronemap:workload -c 'import sys; from pathlib import Path; sys.path.insert(0, "/app/scripts"); import run_stage; run_stage.validate(Path("/outputs"), require_parallel=True); print("Validated native scientific products and actual worker overlap without modifying results")'
