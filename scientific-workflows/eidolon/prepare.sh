#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$root/scripts/acquire.py"
go run "$root/../../tools/showcase/main.go" -root "$root" -prepare-container
