"""Run the 257-activity projection at four capacities and compare results."""

import argparse
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from generate import CAPACITIES, ROOT, WORKFLOW

OUTPUTS = {"projection.csv", "projection.png", "depth-scan.gif"}


def projection(run_id):
    endpoint = os.environ["AKOFLOW_API_URL"].rstrip("/")
    request = Request(f"{endpoint}/execution-runs/{run_id}/",
                      headers={"Authorization": f"Bearer {os.environ['AKOFLOW_API_TOKEN']}"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code != 404:
            raise
        return None


def capture(result, slots):
    activities = result["activities"]
    tiles = [task for task in activities if task["activityId"].startswith(f"{WORKFLOW}-tile-")]
    aggregate = [task for task in activities if task["activityId"] == f"{WORKFLOW}-aggregate"]
    if len(activities) != 257 or len(tiles) != 256 or len(aggregate) != 1:
        raise ValueError("Unexpected tile or aggregation count")
    if any(task["status"] != "completed" for task in activities):
        raise ValueError("An activity did not complete")
    reducer, = aggregate
    expected = {task["activityId"].removeprefix(f"{WORKFLOW}-") + ".csv"
                for task in tiles} | OUTPUTS
    artifacts = [item for item in result["dataObjects"] if item["relativePath"] in expected]
    if len(expected) != 259 or Counter(item["relativePath"] for item in artifacts) != Counter(expected):
        raise ValueError("Missing or repeated result artifacts")
    digests = {item["relativePath"]: item["checksum"] for item in artifacts}
    if not all(digests.values()):
        raise ValueError("Missing result checksum")
    events = Counter()
    unusable = 0
    for task in tiles:
        start, end = task["startedAt"], task["finishedAt"]
        if not 0 < start < end <= reducer["startedAt"]:
            unusable += 1
            continue
        events[start] += 1
        events[end] -= 1
    active = peak = 0
    for instant in sorted(events):
        active += events[instant]
        peak = max(peak, active)
    if not 1 <= peak <= slots:
        raise ValueError("Unexpected measured overlap")
    run = result["run"]
    elapsed = (datetime.fromisoformat(run["finishedAt"]) -
               datetime.fromisoformat(run["startedAt"])).total_seconds()
    return {"run": run["id"], "slots": slots, "completed_activities": len(activities),
            "elapsed_seconds": elapsed, "peak_overlap_lower_bound": peak,
            "unusable_tile_intervals": unusable,
            "aggregate_prepare_seconds": reducer["startedAt"] - reducer["queuedAt"],
            "aggregate_seconds": reducer["finishedAt"] - reducer["startedAt"], "digests": digests}


def profile(directory, slots):
    identifier = f"{WORKFLOW}-run-{slots}"
    if projection(identifier) is None:
        env = dict(os.environ, AKOFLOW_SUBMIT="1", AKOFLOW_RUN_ID=identifier,
                   AKOFLOW_PLAN_FILE=f"plan-{slots}.yaml",
                   AKOFLOW_PLAN_ID=f"{WORKFLOW}-plan-{slots}")
        with (directory / f"{identifier}.log").open("a") as log:
            subprocess.run([ROOT / "run.sh"], env=env, stdout=log, stderr=log, check=True)
    while True:
        try:
            result = projection(identifier)
        except (URLError, TimeoutError):
            time.sleep(10)
            continue
        if result is not None:
            status = result["run"]["status"]
            if status == "completed":
                return capture(result, slots)
            if status not in {"created", "pending", "queued", "running"}:
                raise RuntimeError(f"{identifier} ended with {status}")
        time.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    baseline = None
    for slots in (4, *(capacity for capacity in CAPACITIES if capacity != 4)):
        result = profile(args.directory, slots)
        if baseline is not None and result["digests"] != baseline:
            raise ValueError(f"Scientific checksums differ for {slots} slots")
        baseline = result["digests"]
        path = args.directory / f"{result['run']}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2) + "\n")
        temporary.replace(path)
        print(f"Verified {result['run']}", flush=True)
