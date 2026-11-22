#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd); image=${AKOFLOW_IMAGE:-akoflow/community-pdebench-advection:v1}; output=${AKOFLOW_OUTPUT:-$root/outputs/preflight-$(date +%Y%m%dT%H%M%S)}; docker_cmd=${DOCKER_CMD:-sudo -n docker}
mkdir -p "$output/run-a" "$output/run-b"
run(){ target=$1; shift; $docker_cmd run --rm --network none --user "$(id -u):$(id -g)" -v "$target:/work" "$image" "$@"; }
execute(){ target=$1; run "$target" prepare --output /work; run "$target" infer --model fno --output /work; run "$target" infer --model unet --output /work; run "$target" metrics --model fno --output /work; run "$target" metrics --model unet --output /work; run "$target" compare --output /work; }
execute "$output/run-a"; execute "$output/run-b"
$docker_cmd run --rm --network none --user "$(id -u):$(id -g)" \
  -v "$output/run-a:/work" -v "$output/run-b:/reference:ro" \
  "$image" validate --output /work --reference /reference
printf '%s\n' "$output"
