"""Resume the microscopy reference and short profiles and validate daemon evidence."""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from generate import CAPACITIES, PREFIX, ROOT

OUTPUTS = ("sequence-metrics.csv.gz", "condition-summary.csv",
           "stabilization-residuals.png", "stabilization.gif")


def projection(run_id):
    api = os.getenv("AKOFLOW_API_URL", "http://127.0.0.1:8080/akoflow-api").rstrip("/")
    token = os.getenv("AKOFLOW_API_TOKEN", "akoflow-development-token")
    request = urllib.request.Request(f"{api}/execution-runs/{run_id}/",
                                     headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def capture(result, workflow, count, slots):
    cases = {f"{workflow}-case-{i:03d}" for i in range(count)}
    aggregate_id = f"{workflow}-aggregate"
    activities = result["activities"]
    if Counter(item["activityId"] for item in activities) != Counter(cases | {aggregate_id}):
        raise ValueError("Unexpected or repeated activity")
    if any(item["status"] != "completed" for item in activities):
        raise ValueError("An activity did not complete")
    paths = {f"case-{i:03d}.csv" for i in range(count)} | set(OUTPUTS)
    registered = [item for item in result["dataObjects"] if item["relativePath"] in paths]
    if Counter(item["relativePath"] for item in registered) != Counter(paths):
        raise ValueError("Missing or repeated result artifact")
    digests = {item["relativePath"]: item["checksum"] for item in registered}
    if not all(digests.values()):
        raise ValueError("Missing artifact digest")
    aggregate = next(item for item in activities if item["activityId"] == aggregate_id)
    changes = Counter()
    for item in activities:
        if item is aggregate:
            continue
        start, finish = item["startedAt"], item["finishedAt"]
        if not 0 < start < finish <= aggregate["startedAt"]:
            raise ValueError("Invalid activity order or timestamps")
        changes[start] += 1
        changes[finish] -= 1
    running = peak = 0
    for timestamp in sorted(changes):
        running += changes[timestamp]
        peak = max(peak, running)
    if not 1 <= peak <= slots:
        raise ValueError(f"Observed {peak} simultaneous cases with {slots} slots")
    return {"run": result["run"], "slots": slots, "cases": count,
            "peak_overlapping_cases": peak, "digests": digests, "activities": activities,
            "artifacts": registered, "artifact_locations": result["dataLocations"]}


def run(directory, workflow, count, slots, baseline=None):
    identifier = f"{workflow}-run-{slots}"
    if projection(identifier) is None:
        env = dict(os.environ, AKOFLOW_SUBMIT="1", AKOFLOW_WORKFLOW_ID=workflow,
                   AKOFLOW_RUN_ID=identifier, AKOFLOW_PLAN_FILE=f"plan-{slots}.yaml",
                   AKOFLOW_PLAN_ID=f"{workflow}-plan-{slots}")
        with (directory / f"{identifier}.log").open("a") as log:
            subprocess.run([ROOT / "run.sh"], env=env, stdout=log, stderr=log, check=True)
    while True:
        try:
            result = projection(identifier)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(10)
            continue
        if result is not None:
            status = result["run"]["status"]
            if status == "completed":
                break
            if status in {"failed", "cancelled", "canceled", "aborted"}:
                raise RuntimeError(f"{identifier} ended with {status}: {result['run'].get('failureReason')}")
        time.sleep(10)
    evidence = capture(result, workflow, count, slots)
    if baseline is not None and evidence["digests"] != baseline:
        raise ValueError(f"Scientific results differ in {identifier}")
    path = directory / f"{identifier}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(evidence, indent=2) + "\n")
    temporary.replace(path)
    print(f"Verified {identifier}", flush=True)
    return evidence["digests"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe")
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, ROOT / "generate.py", args.recipe], check=True)
    run(args.evidence, f"{PREFIX}-ensemble-v1", 768, 4)
    subprocess.run([sys.executable, ROOT / "generate.py", args.recipe, "--cases", "48"], check=True)
    baseline = None
    for slots in CAPACITIES:
        baseline = run(args.evidence, f"{PREFIX}-profile-v1", 48, slots, baseline)


if __name__ == "__main__":
    main()
