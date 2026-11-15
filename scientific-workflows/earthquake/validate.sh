#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker run --rm --network none --user "$(id -u):$(id -g)" --env HOME=/tmp --mount "type=bind,src=$root/outputs,dst=/outputs" akoflow-local/earthquake:workload python /app/scripts/validate.py
