#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
api=${AKOFLOW_API_URL:-http://127.0.0.1:8080/akoflow-api}
token=${AKOFLOW_API_TOKEN:-akoflow-development-token}
run_id=${AKOFLOW_RUN_ID:-community-oceanbench-glonet-run-v3}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
request(){ method=$1; endpoint=$2; shift 2; curl --fail-with-body -sS -X "$method" -H "Authorization: Bearer $token" "$@" "$api/$endpoint/"; }
create(){ endpoint=$1; file=$2; request POST "$endpoint" -H 'Content-Type: application/yaml' --data-binary "@$root/$file" > "$tmp/r.json" || true; }
create environments environment.yaml; create execution-scopes scope.yaml; create network-topologies topology.yaml; create workflow-definitions workflow.yaml; create schedule-plans/import plan.yaml
request GET environments/community-oceanbench-parallel > "$tmp/env.json"
request GET execution-scopes/community-oceanbench-parallel-scope > "$tmp/scope.json"
request GET network-topologies/community-oceanbench-parallel-topology > "$tmp/topology.json"
request GET workflow-definitions/community-oceanbench-glonet-v3 > "$tmp/workflow.json"
request GET schedule-plans/community-oceanbench-glonet-plan-v3 > "$tmp/plan.json"
jq -n --arg run_id "$run_id" --slurpfile environment "$tmp/env.json" --slurpfile scope "$tmp/scope.json" --slurpfile topology "$tmp/topology.json" --slurpfile workflow "$tmp/workflow.json" --slurpfile plan "$tmp/plan.json" '{run:{id:$run_id,schedulePlanId:$plan[0].id,mode:"real",status:"created"},plan:$plan[0],workflow:$workflow[0].version,resources:$environment[0].resources,executionScope:$scope[0],runtimes:$environment[0].runtimes,runtimeBindings:$environment[0].resourceRuntimeBindings,networkTopology:$topology[0],activityProfiles:($environment[0].activityResourceProfiles//[])}' > "$tmp/execution.json"
request POST execution-preflights -H 'Content-Type: application/json' --data-binary "@$tmp/execution.json" > "$tmp/preflight.json"
jq . "$tmp/preflight.json"; test "$(jq -r '.ready' "$tmp/preflight.json")" = true
if [ "${AKOFLOW_SUBMIT:-0}" != 1 ]; then echo "Preflight passed; set AKOFLOW_SUBMIT=1 to submit."; exit 0; fi
request POST execution-runs -H 'Content-Type: application/json' -H "Idempotency-Key: $run_id" --data-binary "@$tmp/execution.json"
