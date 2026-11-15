#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v go >/dev/null
command -v docker >/dev/null
docker build -f "$root/docker/Dockerfile" -t akoflow-earthquake-prepare "$root"
docker run --rm --user "$(id -u):$(id -g)" --env HOME=/tmp --mount "type=bind,src=$root/data,dst=/app/data" akoflow-earthquake-prepare python /app/scripts/freeze_catalog.py
go run "$root/../../tools/showcase/main.go" -root "$root" -prepare-container
