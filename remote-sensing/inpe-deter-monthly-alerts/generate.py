"""Write the fixed DAG and three scheduling profiles from the same task list."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREFIX = "community-inpe-deter-portable"
WORKFLOW = f"{PREFIX}-ensemble-v1"
RUNTIME = f"{PREFIX}-local"
ENVIRONMENT = f"{PREFIX}-cpu"
ENV_VERSION = f"{ENVIRONMENT}-v1"
SCOPE = f"{PREFIX}-scope"
TOPOLOGY = f"{PREFIX}-topology"
BATCHES = [f"month-{year}-{month:02d}" for year in range(2019, 2025) for month in range(1, 13)]
ACTIVITIES = ["prepare", *BATCHES, "aggregate"]


def write(name, document):
    (ROOT / name).write_text(json.dumps(document, indent=2) + "\n")


def workflow(build_reference):
    image = {"source": {"type": "build", "artifactBuildRef": build_reference},
             "delivery": {"strategy": "auto", "targetFormat": "oci"}}
    activities = []
    for name in ACTIVITIES:
        command = ["/app/scripts/prepare.py"]
        dependencies = []
        if name.startswith("month-"):
            command = ["/app/scripts/audit_month.py", name.removeprefix("month-"), "/app/snapshot", "."]
            dependencies = ["prepare"]
        elif name == "aggregate":
            command = ["/app/scripts/aggregate.py", ".", "/app/snapshot", "/app/reference.csv", "."]
            dependencies = BATCHES
        activity = {"name": name, "runtime": RUNTIME, "cpuLimit": "1", "memoryLimit": "768Mi",
                    "command": {"executable": image, "entrypoint": "python3", "arguments": command}}
        if dependencies:
            activity["dependsOn"] = dependencies
        activities.append(activity)
    write("workflow.yaml", {"name": WORKFLOW, "spec": {"namespace": "community-explorer",
                                                      "activities": activities}})


def configuration():
    slots = [f"{PREFIX}-slot-{index:02d}" for index in range(8)]
    resources = [
        {"id": slot, "environmentVersionId": ENV_VERSION, "type": "machine",
         "name": f"Local Docker slot {index}", "providerId": f"local-docker-inpe-deter-portable-{index}",
         "cpuCores": 1, "cpuCapacity": 1, "memoryBytes": 1073741824,
         "storageBytes": 1073741824, "computeSpeedup": 1, "pricePerSecond": 0,
         "schedulable": True}
        for index, slot in enumerate(slots)
    ]
    write("environment.yaml", {
        "environment": {"id": ENVIRONMENT, "name": "INPE DETER CPU profiles", "status": "ready"},
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
    write("scope.yaml", {"id": SCOPE, "name": "INPE DETER execution scope", "environmentVersionIds": [ENV_VERSION]})
    write("topology.yaml", {"id": TOPOLOGY, "name": "INPE DETER local topology", "version": 1,
                            "executionScopeId": SCOPE, "links": []})
    for capacity in (1, 4, 8):
        counters = [0] * capacity
        assignments = []
        for name, index in zip(ACTIVITIES, (0, *(i % capacity for i in range(len(BATCHES))), 0)):
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
