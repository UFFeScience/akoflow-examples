#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
go run "$root/../../tools/showcase/main.go" -root "$root" -prepare-container
docker tag akoflow-local/gawa:workload gawa:homeserver-tiles-v1
docker tag akoflow-local/gawa:workload gawa:local-f68f0939d5255163
