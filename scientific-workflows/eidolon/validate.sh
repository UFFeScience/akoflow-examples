#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
result="${AKOFLOW_RESULT_DIR:-$root/outputs}"
docker run --rm --network none --mount "type=bind,src=$result,dst=/outputs,readonly" --mount "type=bind,src=$root/expected,dst=/verification,readonly" --entrypoint python akoflow-local/eidolon:workload /verification/validate.py
