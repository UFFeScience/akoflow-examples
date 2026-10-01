#!/bin/sh
set -eu

api=${AKOFLOW_API_URL:-http://127.0.0.1:8080/akoflow-api}
directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
legacy_root=${AKOFLOW_LEGACY_SCHEDULER_ROOT:-/Users/ovvesley/Workspace/scheduler-simulator}
workflow=${AKOFLOW_MONTAGE_6448_WORKFLOW:-$legacy_root/build/akoflow-validation-minus20/montage-6448/hybrid_hetero/workflow-definition.json}

if [ ! -s "$workflow" ]; then
  echo "Montage-6448 normalized workflow snapshot not found: $workflow" >&2
  exit 1
fi

authorization_header=
if [ -n "${AKOFLOW_API_TOKEN:-}" ]; then
  authorization_header="Authorization: Bearer $AKOFLOW_API_TOKEN"
fi

post() {
  endpoint=$1
  file=$2
  content_type=$3
  if [ -n "$authorization_header" ]; then
    curl -fsS -H "$authorization_header" -H "Content-Type: $content_type" --data-binary "@$file" "$api/$endpoint/"
  else
    curl -fsS -H "Content-Type: $content_type" --data-binary "@$file" "$api/$endpoint/"
  fi
  printf '\n'
}

post environments "$directory/environment.yaml" application/yaml
post execution-scopes "$directory/scope.yaml" application/yaml
post network-topologies "$directory/topology.yaml" application/yaml
post workflow-definitions "$workflow" application/json

echo "Imported Montage-6448, scheduler-hybrid_hetero-v1, its scope, and its topology."
