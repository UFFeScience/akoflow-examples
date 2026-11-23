#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
api=${AKOFLOW_API_URL:-http://127.0.0.1:8080/akoflow-api}
token=${AKOFLOW_API_TOKEN:-akoflow-development-token}
run_id=${AKOFLOW_RUN_ID:-community-caco2-portable-run-v2}
plan_id=community-caco2-tdc-baselines-plan-v2
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT

request() {
  method=$1; endpoint=$2; shift 2
  curl --fail-with-body -sS -X "$method" -H "Authorization: Bearer $token" "$@" "$api/$endpoint/"
}

create_yaml() {
  endpoint=$1; file=$2
  if ! request POST "$endpoint" -H 'Content-Type: application/yaml' --data-binary "@$root/$file" > "$temporary/response.json"; then
    printf 'Registration already exists or was rejected: %s\n' "$endpoint" >&2
  fi
}

create_yaml environments environment.yaml
create_yaml execution-scopes scope.yaml
create_yaml network-topologies topology.yaml
create_yaml workflow-definitions workflow.yaml
create_yaml schedule-plans/import plan.yaml
request GET environments/community-caco2-parallel > "$temporary/environment.json"
request GET execution-scopes/community-caco2-parallel-scope > "$temporary/scope.json"
request GET network-topologies/community-caco2-parallel-topology > "$temporary/topology.json"
request GET workflow-definitions/community-caco2-tdc-baselines-v2 > "$temporary/workflow.json"
request GET "schedule-plans/$plan_id" > "$temporary/plan.json"

jq -n --arg run_id "$run_id" --slurpfile environment "$temporary/environment.json" --slurpfile scope "$temporary/scope.json" \
  --slurpfile topology "$temporary/topology.json" --slurpfile workflow "$temporary/workflow.json" --slurpfile plan "$temporary/plan.json" '
  {run: {id: $run_id, schedulePlanId: $plan[0].id, mode: "real", status: "created"}, plan: $plan[0],
   workflow: $workflow[0].version, resources: $environment[0].resources, executionScope: $scope[0],
   runtimes: $environment[0].runtimes, runtimeBindings: $environment[0].resourceRuntimeBindings,
   networkTopology: $topology[0], activityProfiles: ($environment[0].activityResourceProfiles // [])}' > "$temporary/execution.json"
request POST execution-preflights -H 'Content-Type: application/json' --data-binary "@$temporary/execution.json" > "$temporary/preflight.json"
jq . "$temporary/preflight.json"
request POST execution-runs -H 'Content-Type: application/json' -H "Idempotency-Key: $run_id" --data-binary "@$temporary/execution.json"
printf '\nRun: %s/execution-runs/%s/\n' "$api" "$run_id"
