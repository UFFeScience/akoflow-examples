#!/bin/sh
set -eu
out="${1:-$(mktemp -d)}"
mkdir -p "$out"
chmod 777 "$out"
run() { sudo -n docker run --rm --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=128m --cap-drop ALL --security-opt no-new-privileges -v "$out:/results" akoflow/community-weatherbench2-score-audit:v1 python /app/workflow.py "$@" --output /results; }
run verify
for model in graphcast hres; do for variable in z500 t2m; do run extract --model "$model" --variable "$variable"; done; done
run compare --variable z500
run compare --variable t2m
run aggregate
run animate
run validate
echo "$out"
