#!/bin/sh
set -eu
out="${1:-$(mktemp -d)}"
mkdir -p "$out"
run(){ sudo -n docker run --rm --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -v "$out:/results" akoflow/community-wright-fisher-fixation:v1 python /app/workflow.py "$@" --output /results; }
run prepare
for p in 0.05 0.10 0.25 0.50 0.75; do for s in 0 1 2 3; do run simulate --p0 "$p" --shard "$s"; done; run aggregate --p0 "$p"; done
run render
run validate
echo "$out"
