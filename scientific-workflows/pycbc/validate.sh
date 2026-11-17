#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "${1:-}" = "-definition" ]; then
  exec docker run --rm --network none akoflow-local/pycbc:workload python /app/scripts/validate.py --definition
fi
exec docker run --rm --network none --mount "type=bind,src=$root/outputs,dst=/outputs,readonly" akoflow-local/pycbc:workload python /app/scripts/validate.py
