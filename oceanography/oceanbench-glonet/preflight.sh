#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-oceanbench-glonet:v1}
output=${AKOFLOW_OUTPUT:-$root/outputs/preflight-$(date +%Y%m%dT%H%M%S)}
docker_cmd=${DOCKER_CMD:-sudo -n docker}
test ! -e "$output" || exit 2
mkdir -p "$output"
$docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py prepare --output /work
for branch in glorys-state glorys-mld glorys-geostrophic observations glorys-lagrangian glo12-state glo12-mld glo12-geostrophic glo12-lagrangian; do
  $docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py metric --output /work --branch "$branch"
done
$docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py aggregate --output /work
$docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py render --output /work
$docker_cmd run --rm --network none -v "$output:/work" "$image" python /app/workflow.py validate --output /work
python3 -m json.tool "$output/validation.json"
