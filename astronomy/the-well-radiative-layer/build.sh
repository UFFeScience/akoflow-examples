#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-well-radiative-layer:v1}
docker_cmd=${DOCKER_CMD:-sudo -n docker}
"$root/prepare-inputs.sh"
$docker_cmd build -f "$root/docker/Dockerfile" -t "$image" "$root"
$docker_cmd image inspect --format '{{.Id}}' "$image"
