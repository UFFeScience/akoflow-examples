#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd); a=$(mktemp -d); b=$(mktemp -d); trap 'rm -rf "$a" "$b"' EXIT
d=${DOCKER_CMD:-sudo -n docker}; image=${AKOFLOW_IMAGE:-akoflow/community-jarzynski:v1}
run(){ o=$1; $d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py prepare --output /work
for v in 0.25 0.50 0.75 1.00; do for s in 0 1 2 3; do $d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py shard --output /work --speed "$v" --shard "$s"; done; done
$d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py audit-step --output /work
$d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py audit-euler --output /work
$d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py aggregate --output /work
$d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py render --output /work; }
run "$a"; run "$b"; $d run --rm --network none -v "$b:/work" -v "$a:/reference:ro" "$image" python /app/workflow.py validate --output /work --reference /reference
test "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["overall_pass"])' "$b/validation.json")" = True
rm -rf "$root/outputs/reference"; mkdir -p "$root/outputs/reference"; cp -a "$b/." "$root/outputs/reference/"

