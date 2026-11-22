#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=akoflow/community-stardist-equivariance:v1
output=${1:-"$root/outputs"}

docker_command() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo -n docker "$@"
  fi
}

rm -rf "$output"
mkdir -p "$output"
docker_command run --rm --network none --cpus 1 --memory 2g -v "$output:/work" "$image" python /app/workflow.py prepare --output /work
printf '%s\n' identity r90 r180 r270 reflect reflect-r90 reflect-r180 reflect-r270 |
  xargs -P4 -I{} sh -c 'if docker info >/dev/null 2>&1; then runner=docker; else runner="sudo -n docker"; fi; $runner run --rm --network none --cpus 1 --memory 2g -v "$1:/work" "$2" python /app/workflow.py predict --output /work --transform "$3"' sh "$output" "$image" {}
docker_command run --rm --network none --cpus 1 --memory 2g -v "$output:/work" "$image" python /app/workflow.py aggregate --output /work
docker_command run --rm --network none --cpus 1 --memory 2g -v "$output:/work" "$image" python /app/workflow.py render --output /work
docker_command run --rm --network none --cpus 1 --memory 2g -v "$output:/work" "$image" python /app/workflow.py validate --output /work
(cd "$output" && find . -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > checksums.sha256)
