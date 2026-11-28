"""Generate the tiled projection DAG and scheduling plans."""

import argparse
import json
from functools import partial
from pathlib import Path

from projection import PARTIAL, REFERENCE, tiles


ROOT = Path(__file__).resolve().parent
PREFIX = "community-mip-projection"
WORKFLOW = f"{PREFIX}-ensemble-v1"
RUNTIME = f"{PREFIX}-local"
ENVIRONMENT = f"{PREFIX}-cpu"
ENV_VERSION = f"{ENVIRONMENT}-v1"
SCOPE = f"{PREFIX}-scope"
TOPOLOGY = f"{PREFIX}-topology"
CAPACITIES = (1, 4, 16, 32)
SLOTS = max(CAPACITIES)


def write(name, document, directory=ROOT):
    (directory / name).write_text(json.dumps(document, indent=2) + "\n")


def workflow(build_reference, dataset, partition, batches):
    image = {"source": {"type": "build", "artifactBuildRef": build_reference},
             "delivery": {"strategy": "auto", "targetFormat": "oci"}}
    def activity(name, entrypoint, arguments, dependencies):
        return {
            "name": name, "runtime": RUNTIME, "cpuLimit": "1", "memoryLimit": "768Mi",
            "dependsOn": dependencies,
            "command": {"executable": image, "entrypoint": entrypoint, "arguments": arguments},
        }

    activities = [
        activity(name, "python3", ["/app/artifacts.py", dataset, "tile",
                                  *(str(origin) for origin in tile.start), "."], [])
        for name, tile in zip(batches, partition, strict=True)
    ]
    activities.append(activity("aggregate", "python3",
                               ["/app/artifacts.py", dataset, "aggregate", ".", "."], batches))
    write("workflow.yaml", {"name": WORKFLOW, "spec": {"namespace": "community-explorer",
                                                      "activities": activities}})


def configuration(batches, directory=ROOT):
    save = partial(write, directory=directory)
    activities = [*batches, "aggregate"]
    slots = [f"{PREFIX}-slot-{index:02d}" for index in range(SLOTS)]
    resources = [
        {"id": slot, "environmentVersionId": ENV_VERSION, "type": "machine",
         "name": f"Local Docker projection slot {index}", "providerId": f"local-docker-projection-{index}",
         "cpuCores": 1, "cpuCapacity": 1, "memoryBytes": 1073741824,
         "storageBytes": 1073741824, "computeSpeedup": 1, "pricePerSecond": 0,
         "schedulable": True}
        for index, slot in enumerate(slots)
    ]
    save("environment.yaml", {
        "environment": {"id": ENVIRONMENT, "name": "Tiled intensity projection CPU profiles", "status": "ready"},
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
    save("scope.yaml", {"id": SCOPE, "name": "Tiled intensity projection execution scope", "environmentVersionIds": [ENV_VERSION]})
    save("topology.yaml", {"id": TOPOLOGY, "name": "Tiled intensity projection local topology", "version": 1,
                            "executionScopeId": SCOPE, "links": []})
    for capacity in CAPACITIES:
        counters = [0] * capacity
        assignments = []
        for name, index in zip(activities, (*(i % capacity for i in range(len(batches))), 0)):
            assignments.append({"id": f"{WORKFLOW}-{capacity}-{name}",
                                "activityId": f"{WORKFLOW}-{name}", "resourceId": slots[index],
                                "orderOnResource": counters[index], "metadata": {"runtimeId": RUNTIME}})
            counters[index] += 1
        save(f"plan-{capacity}.yaml", {"plan": {
            "id": f"{WORKFLOW}-plan-{capacity}", "workflowVersionId": f"{WORKFLOW}-v1",
            "executionScopeId": SCOPE, "networkTopologyId": TOPOLOGY, "source": "imported",
            "algorithm": "manual", "algorithmVersion": "1", "objective": "custom",
            "predicted": {"makespanSeconds": 300, "cost": 0, "feasible": True},
            "assignments": assignments,
        }})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_reference", help="Registered portable recipe ID")
    parser.add_argument("--dataset", choices=("standard", "partial"), default="standard")
    args = parser.parse_args()
    if args.dataset == "partial":
        WORKFLOW = f"{PREFIX}-partial-v1"
    partition = tiles(REFERENCE if args.dataset == "standard" else PARTIAL)
    batches = [f"tile-{z:03d}-{y:03d}-{x:03d}" for z, y, x in (tile.start for tile in partition)]
    workflow(args.build_reference, args.dataset, partition, batches)
    configuration(batches)
