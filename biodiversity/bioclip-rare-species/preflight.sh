#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-bioclip-rare-species:v1}
output=${AKOFLOW_OUTPUT:-$root/outputs/preflight-$(date +%Y%m%dT%H%M%S)}

if [ -e "$output" ]; then
  printf 'Output path already exists: %s\n' "$output" >&2
  exit 2
fi
mkdir -p "$output"
docker run --rm -v "$output:/work" "$image" python /app/workflow.py prepare --output /work
for shard in 0 1 2 3 4 5 6 7; do
  docker run --rm --shm-size=1g -v "$output:/work" "$image" python /app/workflow.py infer --output /work --shard "$shard"
done
docker run --rm -v "$output:/work" "$image" python /app/workflow.py aggregate --output /work
docker run --rm -v "$output:/work" "$image" python /app/workflow.py render --output /work
docker run --rm -v "$output:/work" "$image" python /app/workflow.py validate --output /work
python -m json.tool "$output/validation.json"
