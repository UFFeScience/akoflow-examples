#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-turing-schnakenberg:v1}
${DOCKER_CMD:-sudo -n docker} build --pull=false -t "$image" -f "$root/docker/Dockerfile" "$root"
${DOCKER_CMD:-sudo -n docker} image inspect "$image" --format '{{index .RepoDigests 0}} {{.Id}}'
