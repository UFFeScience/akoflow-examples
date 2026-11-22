#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd); out=$(mktemp -d); trap 'rm -rf "$out"' EXIT
docker_cmd=${DOCKER_CMD:-sudo -n docker}; image=${AKOFLOW_IMAGE:-akoflow/community-buffon-needle:v1}
$docker_cmd run --rm --network none -v "$out:/work" "$image" python /app/workflow.py prepare --output /work
for b in seed-1 seed-2 seed-3 seed-4; do $docker_cmd run --rm --network none -v "$out:/work" "$image" python /app/workflow.py sample --output /work --branch "$b"; done
$docker_cmd run --rm --network none -v "$out:/work" "$image" python /app/workflow.py aggregate --output /work
$docker_cmd run --rm --network none -v "$out:/work" "$image" python /app/workflow.py render --output /work
$docker_cmd run --rm --network none -v "$out:/work" "$image" python /app/workflow.py validate --output /work
test "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["overall_pass"])' "$out/validation.json")" = True
