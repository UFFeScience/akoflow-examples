#!/bin/sh
set -eu
mkdir -p outputs
# The daemon workflow expresses parallel members; standalone execution uses the same real stages.
docker run --rm --network none --cpus 2 --memory 8g -v "$PWD/outputs:/work" ghcr.io/uffescience/openoil-ensemble:v1 sh -c '
python /opt/openoil/workflow.py --stage prepare --members 32
i=0
while [ "$i" -lt 32 ]; do stage=$(printf "member-%03d" "$i"); python /opt/openoil/workflow.py --stage "$stage" --members 32; i=$((i+1)); done
for stage in aggregate map summary animate validate; do python /opt/openoil/workflow.py --stage "$stage" --members 32; done'
