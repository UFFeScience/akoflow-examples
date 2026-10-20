#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v go >/dev/null || { echo 'Install Go before running this example.' >&2; exit 1; }
go -C "$root/../.." mod download
command -v python3 >/dev/null || { echo 'Install Python 3 before running this example.' >&2; exit 1; }
if [ -s "$root/requirements.txt" ]; then
  python3 -m venv "$root/.venv"
  "$root/.venv/bin/python" -m pip install -r "$root/requirements.txt"
else
  printf 'No additional Python packages are required. Run ./run.sh.\n'
fi
if [ "${AKOFLOW_LOCAL_CONTAINER:-0}" = 1 ]; then
  go run "$root/../../tools/showcase/main.go" -root "$root" -prepare-container
fi
