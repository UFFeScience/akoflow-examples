#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-black-scholes:v1}
${DOCKER_CMD:-sudo -n docker} build --pull=false -t "$image" -f "$root/docker/Dockerfile" "$root"
${DOCKER_CMD:-sudo -n docker} image inspect "$image" --format '{{.Id}}'
