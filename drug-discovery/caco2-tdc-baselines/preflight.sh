#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=${AKOFLOW_IMAGE:-akoflow/community-caco2-tdc-baselines:v1}
output=${AKOFLOW_OUTPUT:-$root/outputs/preflight-$(date +%Y%m%dT%H%M%S)}

if [ -e "$output" ]; then
  printf 'Output path already exists: %s\n' "$output" >&2
  exit 2
fi
mkdir -p "$output"
docker run --rm -v "$output:/work" "$image" python /app/workflow.py prepare --output /work
for model in morgan rdkit2d cnn; do
  for seed in 1 2 3 4 5; do
    docker run --rm -v "$output:/work" "$image" python /app/workflow.py train --output /work --model "$model" --seed "$seed"
  done
done
docker run --rm -v "$output:/work" "$image" python /app/workflow.py aggregate --output /work
docker run --rm -v "$output:/work" "$image" python /app/workflow.py render --output /work
docker run --rm -v "$output:/work" "$image" python /app/workflow.py validate --output /work
python -m json.tool "$output/validation.json"
