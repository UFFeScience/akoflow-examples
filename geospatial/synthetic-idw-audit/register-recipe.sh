#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
api=${AKOFLOW_API_URL:-http://127.0.0.1:8080/akoflow-api}
token=${AKOFLOW_API_TOKEN:-akoflow-development-token}
context=$(mktemp)
trap 'rm "$context"' EXIT
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$root" \
    -cf - docker/Dockerfile requirements.txt scripts/study.py scripts/render.py \
    evidence/samples.json evidence/samples.sha256 | gzip -n > "$context"
curl --fail-with-body -sS -H "Authorization: Bearer $token" \
    -F "context=@$context;filename=context.tar.gz" -F recipePath=docker/Dockerfile \
    -F platform=linux/amd64 "$api/artifacts/recipe/" | jq -er '.build.id'
