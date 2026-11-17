import json
import os
import time
import urllib.request

BASE = 'http://127.0.0.1:18080/akoflow-api/'

def api(path, body=None):
    request = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                    headers={'Authorization': 'Bearer ' + os.environ['AKOFLOW_API_TOKEN'],
                                             'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)

source = 'akoflow://hub/publications/44bceae5-8081-4d98-9e51-7b24ef0b56be/versions/4'
workflow = api('hub/workflows/import/', {'uri': source, 'name': 'eidolon-arm64-proof'})
version = workflow['version']
resource = dict(id='native-arm', providerId='native-arm', parentResourceId='native-arm',
                environmentVersionId='arm-v1', name='ARM64 Docker', type='machine', architecture='arm64',
                cpuCores=2, cpuCapacity=2, memoryBytes=8589934592, storageBytes=21474836480, schedulable=True)
runtime = dict(id='native-docker', name='Docker', mode='execution', driver='local', role='compute',
               environmentVersionId='arm-v1')
bindings = [dict(resourceId=resource['id'], runtimeId=runtime['id'], enabled=True)]
api('environments/', dict(environment=dict(id='arm', name='ARM64'), version=dict(id='arm-v1', version=1),
                          resources=[resource], runtimes=[runtime], resourceRuntimeBindings=bindings))
scope = dict(id='arm-scope', name='Native ARM64', environmentVersionIds=['arm-v1'])
api('execution-scopes/', scope)
topology = dict(id='arm-topology', name='Local ARM64', version=1, executionScopeId=scope['id'], links=[])
api('network-topologies/', topology)
remaining = {a['id'] for a in version['activities']}
dependencies = {}
for dependency in version['dependencies'] or []:
    dependencies.setdefault(dependency['activityId'], set()).add(dependency['dependsOnActivityId'])
ordered = []
while remaining:
    ready = sorted(a for a in remaining if dependencies.get(a, set()).issubset(ordered))
    assert ready, 'Workflow has a cycle'
    ordered.extend(ready)
    remaining.difference_update(ready)
plan = dict(id='eidolon-native-plan', workflowVersionId=version['id'], executionScopeId=scope['id'],
            networkTopologyId=topology['id'], source='manual', algorithm='manual', objective='custom',
            predicted=dict(feasible=True, makespanSeconds=len(ordered)+1),
            assignments=[dict(id=f'arm-assignment-{i}', activityId=activity, resourceId=resource['id'],
                              orderOnResource=i+1, predictedStartAt=i+1, predictedFinishAt=i+2,
                              predictedRuntimeSeconds=1) for i,activity in enumerate(ordered)])
api('schedule-plans/', dict(plan=plan, workflow=version, resources=[resource],
                           executionScope=scope, networkTopology=topology))
run = 'eidolon-v4-native-arm64'
api('execution-runs/', dict(run=dict(id=run, mode='real'), plan=plan, workflow=version,
                            executionScope=scope, networkTopology=topology, resources=[resource],
                            runtimes=[runtime], runtimeBindings=bindings))
for i in range(180):
    state = api(f'execution-runs/{run}/status/')
    status = state.get('run', state)['status']
    if status in ('completed', 'failed', 'cancelled'):
        for view in ('status', 'logs', 'artifacts', 'events'):
            with open(f'eidolon-{view}.json','w') as output:
                json.dump(api(f'execution-runs/{run}/{view}/'),output,indent=2)
        print(json.dumps(dict(source=source, architecture=os.uname().machine, run=run,
                              expectedActivities=len(ordered), status=status)), flush=True)
        assert status=='completed', json.dumps(state)
        break
    time.sleep(5)
else:
    raise RuntimeError('Timed out waiting for Eidolon')
