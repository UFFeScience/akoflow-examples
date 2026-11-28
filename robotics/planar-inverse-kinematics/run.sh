#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
configuration=${AKOFLOW_CONFIG_DIR:-$root}
api=${AKOFLOW_API_URL:-http://127.0.0.1:8080/akoflow-api}
token=${AKOFLOW_API_TOKEN:-akoflow-development-token}
workflow=${AKOFLOW_WORKFLOW_ID:-community-planar-kinematics-ensemble-v1}
run_id=${AKOFLOW_RUN_ID:-$workflow-run-4}
plan_file=${AKOFLOW_PLAN_FILE:-plan-4.yaml}
plan_id=${AKOFLOW_PLAN_ID:-$workflow-plan-4}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
request(){ method=$1; endpoint=$2; shift 2; curl --fail-with-body -sS -X "$method" -H "Authorization: Bearer $token" "$@" "$api/$endpoint/"; }
create(){ endpoint=$1; file=$2; request POST "$endpoint" -H 'Content-Type: application/yaml' --data-binary "@$configuration/$file" > "$tmp/r.json" || true; }
if [ "${AKOFLOW_USE_IMPORTED_WORKFLOW:-0}" = 1 ]; then
    request GET workflow-definitions/"$workflow" > "$tmp/workflow.json"
fi
create environments environment.yaml
create execution-scopes scope.yaml
create network-topologies topology.yaml
if [ "${AKOFLOW_USE_IMPORTED_WORKFLOW:-0}" != 1 ]; then
    create workflow-definitions workflow.yaml
    request GET workflow-definitions/"$workflow" > "$tmp/workflow.json"
fi
create schedule-plans/import "$plan_file"
request GET environments/community-planar-kinematics-cpu > "$tmp/env.json"
request GET execution-scopes/community-planar-kinematics-scope > "$tmp/scope.json"
request GET network-topologies/community-planar-kinematics-topology > "$tmp/topology.json"
request GET schedule-plans/"$plan_id" > "$tmp/plan.json"
jq -n --arg run_id "$run_id" --slurpfile environment "$tmp/env.json" --slurpfile scope "$tmp/scope.json" --slurpfile topology "$tmp/topology.json" --slurpfile workflow "$tmp/workflow.json" --slurpfile plan "$tmp/plan.json" '{run:{id:$run_id,schedulePlanId:$plan[0].id,mode:"real",status:"created"},plan:$plan[0],workflow:$workflow[0].version,resources:$environment[0].resources,executionScope:$scope[0],runtimes:$environment[0].runtimes,runtimeBindings:$environment[0].resourceRuntimeBindings,networkTopology:$topology[0],activityProfiles:($environment[0].activityResourceProfiles//[])}' > "$tmp/execution.json"
request POST execution-preflights -H 'Content-Type: application/json' --data-binary "@$tmp/execution.json" > "$tmp/preflight.json"
jq . "$tmp/preflight.json"
test "$(jq -r '.ready' "$tmp/preflight.json")" = true
jq --arg id "$(jq -r '.id' "$tmp/preflight.json")" '.preflightId=$id' "$tmp/execution.json" > "$tmp/ready.json"; mv "$tmp/ready.json" "$tmp/execution.json"
if [ "${AKOFLOW_SUBMIT:-0}" != 1 ]; then echo 'Preflight passed; set AKOFLOW_SUBMIT=1 to submit.'; exit 0; fi
request POST execution-runs -H 'Content-Type: application/json' -H "Idempotency-Key: $run_id" --data-binary "@$tmp/execution.json"
