"""Write the fixed DAG and four scheduling profiles from the same task list."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREFIX = "community-ngspice-rlc"
WORKFLOW = f"{PREFIX}-ensemble-v1"
RUNTIME = f"{PREFIX}-local"
ENVIRONMENT = f"{PREFIX}-cpu"
ENV_VERSION = f"{ENVIRONMENT}-v1"
SCOPE = f"{PREFIX}-scope"
TOPOLOGY = f"{PREFIX}-topology"
BATCHES = [f"batch-{index:03d}" for index in range(128)]
ACTIVITIES = ["prepare", *BATCHES, "aggregate"]


def write(name, document):
    (ROOT / name).write_text(json.dumps(document, indent=2) + "\n")


def workflow(build_reference):
    image = {"source": {"type": "build", "artifactBuildRef": build_reference},
             "delivery": {"strategy": "auto", "targetFormat": "oci"}}
    activities = []
    for name in ACTIVITIES:
        command = ["/app/scripts/rlc.py", "prepare"]
        dependencies = []
        if name.startswith("batch-"):
            command = ["/app/scripts/rlc.py", "batch", "--batch", str(int(name.rsplit("-", 1)[1]))]
            dependencies = ["prepare"]
        elif name == "aggregate":
            command = ["/app/scripts/aggregate.py"]
            dependencies = BATCHES
        activity = {"name": name, "runtime": RUNTIME, "cpuLimit": "1", "memoryLimit": "768Mi",
                    "command": {"executable": image, "entrypoint": "python3", "arguments": command}}
        if dependencies:
            activity["dependsOn"] = dependencies
        activities.append(activity)
    write("workflow.yaml", {"name": WORKFLOW, "spec": {"namespace": "community-explorer",
                                                      "activities": activities}})


def configuration():
    slots = [f"{PREFIX}-slot-{index:02d}" for index in range(16)]
    resources = [
        {"id": slot, "environmentVersionId": ENV_VERSION, "type": "machine",
         "name": f"Local Docker slot {index}", "providerId": f"local-docker-ngspice-rlc-{index}",
         "cpuCores": 1, "cpuCapacity": 1, "memoryBytes": 1073741824,
         "storageBytes": 1073741824, "computeSpeedup": 1, "pricePerSecond": 0,
         "schedulable": True}
        for index, slot in enumerate(slots)
    ]
    write("environment.yaml", {
        "environment": {"id": ENVIRONMENT, "name": "RLC CPU profiles", "status": "ready"},
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
    write("scope.yaml", {"id": SCOPE, "name": "RLC execution scope", "environmentVersionIds": [ENV_VERSION]})
    write("topology.yaml", {"id": TOPOLOGY, "name": "RLC local topology", "version": 1,
                            "executionScopeId": SCOPE, "links": []})
    for capacity in (1, 4, 8, 16):
        counters = [0] * capacity
        assignments = []
        for name, index in zip(ACTIVITIES, (0, *(i % capacity for i in range(128)), 0)):
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
