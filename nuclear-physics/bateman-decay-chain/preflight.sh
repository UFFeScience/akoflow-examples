#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd); a=$(mktemp -d); b=$(mktemp -d); trap 'rm -rf "$a" "$b"' EXIT
d=${DOCKER_CMD:-sudo -n docker}; image=${AKOFLOW_IMAGE:-akoflow/community-bateman-decay:v1}
run(){ o=$1; $d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py prepare --output /work; for x in transient secular repeated; do $d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py solve --output /work --branch "$x"; done; $d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py aggregate --output /work; $d run --rm --network none -v "$o:/work" "$image" python /app/workflow.py render --output /work; }
run "$a"; run "$b"; $d run --rm --network none -v "$b:/work" -v "$a:/reference:ro" "$image" python /app/workflow.py validate --output /work --reference /reference
test "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["overall_pass"])' "$b/validation.json")" = True
