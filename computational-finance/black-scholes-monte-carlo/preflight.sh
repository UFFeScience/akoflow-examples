#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-black-scholes:v1}
output=${AKOFLOW_OUTPUT:-$root/outputs/preflight}
docker_cmd=${DOCKER_CMD:-sudo -n docker}
test ! -e "$output" || exit 2
mkdir -p "$output/a" "$output/b"
run(){ target=$1; shift; $docker_cmd run --rm --network none --cpus 1 --memory 1g --user "$(id -u):$(id -g)" -v "$target:/work" "$image" python /app/workflow.py "$@"; }
execute(){ target=$1; run "$target" prepare --output /work; for seed in 20261123 20261124 20261125 20261126; do run "$target" estimate --output /work --seed "$seed"; done; run "$target" aggregate --output /work; run "$target" render --output /work; }
execute "$output/a"
execute "$output/b"
$docker_cmd run --rm --network none --cpus 1 --memory 1g --user "$(id -u):$(id -g)" -v "$output/a:/work" -v "$output/b:/reference:ro" "$image" python /app/workflow.py validate --output /work --reference /reference
