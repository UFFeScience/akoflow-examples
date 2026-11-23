#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd); image=${AKOFLOW_IMAGE:-akoflow/community-percolation:v1}; output=${AKOFLOW_OUTPUT:-$root/outputs/preflight}; docker_cmd=${DOCKER_CMD:-sudo -n docker}
test ! -e "$output" || exit 2; mkdir -p "$output/a" "$output/b"
run(){ target=$1; shift; $docker_cmd run --rm --network none --cpus 1 --memory 1g --user "$(id -u):$(id -g)" -v "$target:/work" "$image" python /app/workflow.py "$@"; }
execute(){ target=$1; run "$target" prepare --output /work; for L in 32 64 128 256; do for s in 0 1 2 3; do run "$target" shard --output /work --size "$L" --shard "$s"; done; done; run "$target" aggregate --output /work; run "$target" render --output /work; }
execute "$output/a"; execute "$output/b"
$docker_cmd run --rm --network none --cpus 1 --memory 1g --user "$(id -u):$(id -g)" -v "$output/a:/work" -v "$output/b:/reference:ro" "$image" python /app/workflow.py validate --output /work --reference /reference
