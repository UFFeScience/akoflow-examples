#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "${1:-}" = "-definition" ]; then
  exec docker run --rm --network none akoflow-local/rnaseq:workload python3 /app/scripts/validate.py --definition
fi
exec docker run --rm --network none --mount "type=bind,src=$root/outputs,dst=/outputs,readonly" akoflow-local/rnaseq:workload python3 /app/scripts/validate.py
