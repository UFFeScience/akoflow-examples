#!/usr/bin/env bash
set -euo pipefail

source_image=${MONTAGE_IMAGE:-ovvesley/akoflow-wf-montage@sha256:26b060b83b990557ea86ab40503cc8f17ab6016b5973e7e6f9201100a96440c9}
target_image=${CALIBRATION_IMAGE:-akoflow/montage-58-interference-calibration:050d}
script_directory=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
experiment_directory=$(cd "$script_directory/.." && pwd)

docker pull "$source_image"
docker build --pull=false \
  --platform linux/amd64 \
  --build-arg "BASE_IMAGE=$source_image" \
  --tag "$target_image" \
  --file "$experiment_directory/docker/Dockerfile" \
  "$experiment_directory/docker"

docker run --rm --platform linux/amd64 "$target_image" \
  sh -c 'cd /akoflow-wfa-shared && sha256sum -c /akoflow-calibration/projected-inputs.sha256'

printf 'Prepared calibration image: %s\n' "$target_image"
docker image inspect "$target_image" --format 'Image ID: {{.Id}}'
