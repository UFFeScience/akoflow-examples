#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd);image=${AKOFLOW_IMAGE:-akoflow/community-ising-yang:v1};output=${AKOFLOW_OUTPUT:-$root/outputs/preflight-$(date +%Y%m%dT%H%M%S)};docker_cmd=${DOCKER_CMD:-sudo -n docker}
test ! -e "$output" || exit 2;mkdir -p "$output/run-a" "$output/run-b"
run(){ target=$1;shift;$docker_cmd run --rm --network none --cpus 1 --memory 1g --user "$(id -u):$(id -g)" -v "$target:/work" "$image" python /app/workflow.py "$@"; }
execute(){ target=$1;run "$target" prepare --output /work;for shard in 0 1 2 3 4 5 6 7;do run "$target" sample --output /work --shard "$shard";done;run "$target" aggregate --output /work;run "$target" render --output /work; }
execute "$output/run-a";execute "$output/run-b"
$docker_cmd run --rm --network none --cpus 1 --memory 1g --user "$(id -u):$(id -g)" -v "$output/run-a:/work" -v "$output/run-b:/reference:ro" "$image" python /app/workflow.py validate --output /work --reference /reference
$docker_cmd run --rm --network none --cpus 1 --memory 1g --user "$(id -u):$(id -g)" -v "$output/run-b:/work" -v "$output/run-a:/reference:ro" "$image" python /app/workflow.py validate --output /work --reference /reference
python3 -m json.tool "$output/run-a/validation.json"
