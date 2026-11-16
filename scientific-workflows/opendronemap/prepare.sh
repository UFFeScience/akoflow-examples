#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v go >/dev/null
command -v docker >/dev/null
python3 "$root/scripts/prepare_data.py"
go run "$root/../../tools/showcase/main.go" -root "$root" -prepare-container
