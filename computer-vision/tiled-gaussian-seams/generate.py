"""Generate the tiled Gaussian DAG and scheduling plans."""

import argparse
import json
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREFIX = "community-tiled-gaussian"
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


def workflow(build_reference, tile_cases, directory):
    image = {"source": {"type": "build", "artifactBuildRef": build_reference},
             "delivery": {"strategy": "auto", "targetFormat": "oci"}}

    def activity(name, arguments, dependencies):
        return {
            "name": name, "runtime": RUNTIME, "cpuLimit": "1", "memoryLimit": "768Mi",
            "dependsOn": dependencies,
            "command": {"executable": image, "entrypoint": "python3",
                        "arguments": ["/app/artifacts.py", *arguments]},
        }

    names = [tile_name(*case) for case in tile_cases]
    activities = [activity(name, ["tile", *(str(item) for item in case), "."], [])
                  for name, case in zip(names, tile_cases, strict=True)]
    activities.append(activity("aggregate", ["aggregate", ".", "."], names))
    write("workflow.yaml", {"name": WORKFLOW, "spec": {"namespace": "community-explorer",
                                                      "activities": activities}}, directory)


def tile_name(image, kernel, tile):
    return f"tile-{image:02d}-{kernel:02d}-{tile:02d}"


def configuration(batches, directory=ROOT):
    save = partial(write, directory=directory)
    activities = [*batches, "aggregate"]
    slots = [f"{PREFIX}-slot-{index:02d}" for index in range(SLOTS)]
    resources = [
        {"id": slot, "environmentVersionId": ENV_VERSION, "type": "machine",
         "name": f"Local Docker tiled Gaussian slot {index}", "providerId": f"local-docker-tiled-gaussian-{index}",
         "cpuCores": 1, "cpuCapacity": 1, "memoryBytes": 1073741824,
         "storageBytes": 1073741824, "computeSpeedup": 1, "pricePerSecond": 0,
         "schedulable": True}
        for index, slot in enumerate(slots)
    ]
    save("environment.yaml", {
        "environment": {"id": ENVIRONMENT, "name": "Tiled Gaussian CPU profiles", "status": "ready"},
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
    save("scope.yaml", {"id": SCOPE, "name": "Tiled Gaussian execution scope", "environmentVersionIds": [ENV_VERSION]})
    save("topology.yaml", {"id": TOPOLOGY, "name": "Tiled Gaussian local topology", "version": 1,
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
    from gaussian import cases

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_reference", help="Registered portable recipe ID")
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    tile_cases = list(cases())
    workflow(args.build_reference, tile_cases, args.output)
    configuration([tile_name(*case) for case in tile_cases], args.output)
