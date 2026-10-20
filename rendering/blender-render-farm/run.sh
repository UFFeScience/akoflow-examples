#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export AKOFLOW_LOCAL_CONTAINER=${AKOFLOW_LOCAL_CONTAINER:-1}
go run "$root/../../tools/showcase/main.go" -root "$root"
"$root/validate.sh"
