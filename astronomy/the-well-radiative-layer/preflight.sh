#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-well-radiative-layer:v1}
output=${AKOFLOW_OUTPUT:-$root/outputs/preflight-$(date +%Y%m%dT%H%M%S)}
docker_cmd=${DOCKER_CMD:-sudo -n docker}
test ! -e "$output" || { echo "Output exists: $output" >&2; exit 2; }
mkdir -p "$output"
$docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py prepare --output /work
for value in 0.03 0.06 0.10 0.18 0.32 0.56 1.00 1.78 3.16; do
  $docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py analyze --output /work --tcool "$value"
done
$docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py aggregate --output /work
$docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py render --output /work
$docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py validate --output /work
python3 -m json.tool "$output/validation.json"
