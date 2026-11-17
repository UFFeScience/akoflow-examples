#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "${1:-}" = "-definition" ]; then
  shift
  exec python3 "$root/scripts/local.py" validate --definition "$@"
fi
exec python3 "$root/scripts/local.py" validate "$@"
