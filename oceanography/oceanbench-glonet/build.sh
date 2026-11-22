#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-oceanbench-glonet:v1}
docker_cmd=${DOCKER_CMD:-sudo -n docker}
test -f "$root/inputs/input-manifest.json" || { echo "Run prepare-inputs.py first" >&2; exit 2; }
$docker_cmd build -f "$root/docker/Dockerfile" -t "$image" "$root"
$docker_cmd image inspect --format '{{.Id}}' "$image"
