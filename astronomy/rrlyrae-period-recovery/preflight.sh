#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=akoflow/community-rrlyrae-period-recovery:v1
output="$root/outputs"

rm -rf "$output"
mkdir -p "$output"
docker run --rm --network none -v "$output:/work" "$image" python /app/workflow.py prepare --output /work
for band in u g r i z multiband; do
  docker run --rm --network none -v "$output:/work" "$image" python /app/workflow.py periodogram --input /work --output /work --band "$band"
done
docker run --rm --network none -v "$output:/work" "$image" python /app/workflow.py aggregate --input /work --output /work
docker run --rm --network none -v "$output:/work" "$image" python /app/workflow.py animate --input /work --output /work
docker run --rm --network none -v "$output:/work" "$image" python /app/workflow.py validate --input /work --output /work
sha256sum "$output"/* > "$output/checksums.sha256"
