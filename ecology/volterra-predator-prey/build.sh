#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-volterra-predator-prey:v1}
docker_cmd=${DOCKER_CMD:-sudo -n docker}
$docker_cmd build -f "$root/docker/Dockerfile" -t "$image" "$root"
$docker_cmd image inspect --format '{{.Id}}' "$image"
