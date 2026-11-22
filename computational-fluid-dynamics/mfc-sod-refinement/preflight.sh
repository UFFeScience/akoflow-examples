#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=akoflow/community-mfc-sod-refinement:v1
output=${MFC_PREFLIGHT_OUTPUT:-"$root/outputs"}

rm -rf "$output"
mkdir -p "$output"
sudo -n docker run --rm --network none -v "$output:/work" "$image" python3 /app/workflow.py prepare --output /work
for n in 100 200 400 800; do
  sudo -n docker run --rm --network none -v "$output:/work" "$image" python3 /app/workflow.py simulate --output /work --resolution "$n"
  sudo -n docker run --rm --network none -v "$output:/work" "$image" python3 /app/workflow.py measure --input /work --output /work --resolution "$n"
done
sudo -n docker run --rm --network none -v "$output:/work" "$image" python3 /app/workflow.py aggregate --input /work --output /work
sudo -n docker run --rm --network none -v "$output:/work" "$image" python3 /app/workflow.py animate --input /work --output /work
sudo -n docker run --rm --network none -v "$output:/work" "$image" python3 /app/workflow.py validate --input /work --output /work
find "$output" -type f -print0 | sort -z | xargs -0 sha256sum > "$output/checksums.sha256"

