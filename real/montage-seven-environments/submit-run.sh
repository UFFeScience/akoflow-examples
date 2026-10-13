#!/bin/sh
set -eu

scenario=${1:?usage: submit-run.sh SCENARIO RUN_ID}
run_id=${2:?usage: submit-run.sh SCENARIO RUN_ID}
api_base=${AKOFLOW_API_URL:-http://127.0.0.1:8080/akoflow-api}
api_token=${AKOFLOW_API_TOKEN:?AKOFLOW_API_TOKEN is required}
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

get() {
  curl --fail-with-body -sS -H "Authorization: Bearer $api_token" "$api_base/$1/"
}

manifest=$(cat "$base/manifest.json")
entry=$(printf '%s' "$manifest" | jq -ec --arg id "$scenario" '.scenarios[] | select(.id==$id)')
plan_id=$(printf '%s' "$entry" | jq -er '.planId')
scope_id=$(printf '%s' "$entry" | jq -er '.scopeId')
network_id=$(printf '%s' "$entry" | jq -er '.networkTopologyId')

plan=$(get "schedule-plans/$plan_id")
workflow=$(get 'workflow-definitions/montage-58-calibrated-real-050d')
scope=$(get "execution-scopes/$scope_id")
network=$(get "network-topologies/$network_id")
catalog=$(get environments)

resources='[]'
runtimes='[]'
bindings='[]'
for version_id in $(printf '%s' "$scope" | jq -r '.environmentVersionIds[]'); do
  environment_id=$(printf '%s' "$catalog" | jq -er --arg version "$version_id" '.[] | select(.version.id==$version) | .environment.id')
  environment=$(get "environments/$environment_id")
  resources=$(printf '%s' "$resources" | jq -c --argjson values "$(printf '%s' "$environment" | jq '.resources')" '. + $values | unique_by(.id)')
  runtimes=$(printf '%s' "$runtimes" | jq -c --argjson values "$(printf '%s' "$environment" | jq '.runtimes')" '. + $values | unique_by(.id)')
  bindings=$(printf '%s' "$bindings" | jq -c --argjson values "$(printf '%s' "$environment" | jq '.resourceRuntimeBindings')" '. + $values | unique_by(.resourceId + ":" + .runtimeId)')
done

payload=$(jq -nc \
  --arg runId "$run_id" \
  --argjson plan "$plan" \
  --argjson workflow "$workflow" \
  --argjson scope "$scope" \
  --argjson network "$network" \
  --argjson resources "$resources" \
  --argjson runtimes "$runtimes" \
  --argjson bindings "$bindings" \
  '{run:{id:$runId,schedulePlanId:$plan.id,mode:"real",status:"created"},
    plan:$plan,workflow:$workflow.version,executionScope:$scope,networkTopology:$network,
    resources:$resources,runtimes:$runtimes,runtimeBindings:$bindings}')

if [ "${AKOFLOW_DRY_RUN:-false}" = true ]; then
  printf '%s\n' "$payload"
else
  printf '%s' "$payload" | curl --fail-with-body -sS \
    -H "Authorization: Bearer $api_token" -H 'Content-Type: application/json' \
    --data-binary @- "$api_base/execution-runs/"
fi
