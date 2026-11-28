"""Write the fixed DAG and five scheduling profiles from the same task list."""

import argparse
import json
from pathlib import Path

from scripts.study import BLOCKS, block_name, cases

ROOT = Path(__file__).resolve().parent
PREFIX = "community-synthetic-idw"
WORKFLOW = f"{PREFIX}-ensemble-v1"
RUNTIME = f"{PREFIX}-local"
ENVIRONMENT = f"{PREFIX}-cpu"
ENV_VERSION = f"{ENVIRONMENT}-v1"
SCOPE = f"{PREFIX}-scope"
TOPOLOGY = f"{PREFIX}-topology"
PREPARATIONS = [f"prepare-{scenario}" for scenario in range(8)]
BLOCK_TASKS = [(scenario, condition, exponent, block)
               for scenario, condition, exponent in cases() for block in range(BLOCKS)]
BATCHES = [block_name(*task) for task in BLOCK_TASKS]
ACTIVITIES = [*PREPARATIONS, *BATCHES, "aggregate"]


def write(name, document):
    (ROOT / name).write_text(json.dumps(document, indent=2) + "\n")


def workflow(build_reference):
    image = {"source": {"type": "build", "artifactBuildRef": build_reference},
             "delivery": {"strategy": "auto", "targetFormat": "oci"}}
    def activity(name, arguments, dependencies):
        return {
            "name": name, "runtime": RUNTIME, "cpuLimit": "1", "memoryLimit": "768Mi",
            "dependsOn": dependencies,
            "command": {"executable": image, "entrypoint": "python3",
                        "arguments": ["/app/scripts/study.py", *arguments]},
        }

    activities = [
        activity(name, ["prepare", "/app/evidence/samples.json", ".", "--scenario", str(scenario)], [])
        for scenario, name in enumerate(PREPARATIONS)
    ]
    activities += [
        activity(block_name(*task), ["predict", str(task[0]), task[1], str(task[2]), str(task[3]),
                                     f"sites-{task[0]}.json", "."], [PREPARATIONS[task[0]]])
        for task in BLOCK_TASKS
    ]
    activities.append(activity("aggregate", ["assemble", ".", ".", "--render"], PREPARATIONS + BATCHES))
    write("workflow.yaml", {"name": WORKFLOW, "spec": {"namespace": "community-explorer",
                                                      "activities": activities}})


def configuration():
    slots = [f"{PREFIX}-slot-{index:02d}" for index in range(32)]
    resources = [
        {"id": slot, "environmentVersionId": ENV_VERSION, "type": "machine",
         "name": f"Local Docker slot {index}", "providerId": f"local-docker-synthetic-idw-{index}",
         "cpuCores": 1, "cpuCapacity": 1, "memoryBytes": 1073741824,
         "storageBytes": 1073741824, "computeSpeedup": 1, "pricePerSecond": 0,
         "schedulable": True}
        for index, slot in enumerate(slots)
    ]
    write("environment.yaml", {
        "environment": {"id": ENVIRONMENT, "name": "Synthetic IDW CPU profiles", "status": "ready"},
        "version": {"id": ENV_VERSION, "environmentId": ENVIRONMENT, "version": 1,
                    "status": "published", "networkModel": "local", "interferenceModel": "observed",
                    "costModel": "free", "configurationHash": ENV_VERSION},
        "runtimes": [{"id": RUNTIME, "environmentVersionId": ENV_VERSION, "name": "Local Docker",
                      "driver": "local", "mode": "execution", "role": "compute",
                      "capabilities": {"batch": True, "container": True}}],
        "resources": resources, "storages": [], "connections": [], "activityResourceProfiles": [],
        "resourceRuntimeBindings": [{"resourceId": slot, "runtimeId": RUNTIME, "enabled": True}
                                    for slot in slots],
    })
    write("scope.yaml", {"id": SCOPE, "name": "Synthetic IDW execution scope", "environmentVersionIds": [ENV_VERSION]})
    write("topology.yaml", {"id": TOPOLOGY, "name": "Synthetic IDW local topology", "version": 1,
                            "executionScopeId": SCOPE, "links": []})
    for capacity in (1, 4, 8, 16, 32):
        counters = [0] * capacity
        assignments = []
        for name, index in zip(ACTIVITIES, (*(i % capacity for i in range(len(PREPARATIONS))), *(i % capacity for i in range(len(BATCHES))), 0)):
            assignments.append({"id": f"{PREFIX}-{capacity}-{name}",
                                "activityId": f"{WORKFLOW}-{name}", "resourceId": slots[index],
                                "orderOnResource": counters[index], "metadata": {"runtimeId": RUNTIME}})
            counters[index] += 1
        write(f"plan-{capacity}.yaml", {"plan": {
            "id": f"{PREFIX}-plan-{capacity}-v1", "workflowVersionId": f"{WORKFLOW}-v1",
            "executionScopeId": SCOPE, "networkTopologyId": TOPOLOGY, "source": "imported",
            "algorithm": "manual", "algorithmVersion": "1", "objective": "custom",
            "predicted": {"makespanSeconds": 300, "cost": 0, "feasible": True},
            "assignments": assignments,
        }})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_reference", help="Registered portable recipe ID")
    args = parser.parse_args()
    workflow(args.build_reference)
    configuration()
