"""Run five rainfall infiltration scheduling profiles sequentially and capture evidence."""

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = os.environ.get("AKOFLOW_API_URL", "http://127.0.0.1:8080/akoflow-api").rstrip("/")
TOKEN = os.environ.get("AKOFLOW_API_TOKEN", "akoflow-development-token")
CAPACITIES = (1, 4, 8, 16, 32)
DETERMINISTIC = ("infiltration-batches.csv", "rainfall-runoff.png", "rainfall-runoff.gif")


def projection(run_id):
    request = urllib.request.Request(
        f"{API}/execution-runs/{run_id}/", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def run_id(slots, repetition):
    return f"community-rainfall-infiltration-run-{slots}-v1" + (f"-r{repetition}" if repetition > 1 else "")


def check_manifest(result):
    flow = result["activities"]
    expected = {f"community-rainfall-infiltration-ensemble-v1-batch-{index:03d}" for index in range(512)}
    expected |= {"community-rainfall-infiltration-ensemble-v1-prepare", "community-rainfall-infiltration-ensemble-v1-aggregate"}
    if len(flow) != 514 or {item["activityId"] for item in flow} != expected:
        raise ValueError("Unexpected activity inventory")
    if any(item["status"] != "completed" for item in flow):
        raise ValueError("An activity did not complete")
    producers = [item["relativePath"] for item in result["dataObjects"]]
    paths = {f"batch-{index:03d}-results.json" for index in range(512)}
    if set(producers).intersection(paths) != paths or sum(path in paths for path in producers) != 512:
        raise ValueError("Missing or repeated batch artifact")
    digests = {item["relativePath"]: item["checksum"] for item in result["dataObjects"]
               if item["relativePath"] in DETERMINISTIC}
    if set(digests) != set(DETERMINISTIC):
        raise ValueError("Missing infiltration output digests")
    return digests


def save(path, result, slots, repetition):
    digests = check_manifest(result)
    flow = result["activities"]
    scientific = [item for item in flow if "-batch-" in item["activityId"]]
    changes = []
    for item in scientific:
        changes.extend([(item["startedAt"], 1), (item["finishedAt"], -1)])
    active = peak = 0
    for _, delta in sorted(changes):
        active += delta
        peak = max(peak, active)
    run = result["run"]
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({
        "slots": slots, "repetition": repetition,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "run": run, "activities": flow, "max_overlapping_batches": peak,
        "digests": digests,
        "artifacts": result["dataObjects"],
        "artifact_locations": result["dataLocations"],
    }, indent=2) + "\n")
    temporary.replace(path)
    return digests


def wait_for(identifier):
    while True:
        try:
            result = projection(identifier)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(10)
            continue
        if result is not None:
            status = result["run"]["status"]
            if status == "completed":
                return result
            if status in {"failed", "cancelled", "canceled", "aborted"}:
                raise RuntimeError(f"{identifier} ended with {status}: {result['run'].get('failureReason')}")
        time.sleep(10)


def submit(identifier, slots, directory):
    command_env = dict(os.environ, AKOFLOW_RUN_ID=identifier, AKOFLOW_PLAN_FILE=f"plan-{slots}.yaml",
                       AKOFLOW_PLAN_ID=f"community-rainfall-infiltration-plan-{slots}-v1", AKOFLOW_SUBMIT="1")
    with (directory / f"{identifier}.log").open("a") as log:
        subprocess.run([ROOT / "run.sh"], env=command_env, stdout=log, stderr=log, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    # Reuse the initial four-slot run before submitting any additional profile.
    reference_id = run_id(4, 1)
    if projection(reference_id) is None:
        submit(reference_id, 4, args.evidence)
    baseline = save(args.evidence / f"{reference_id}.json", wait_for(reference_id), 4, 1)
    print(f"Verified {reference_id}", flush=True)
    for repetition in (1, 2, 3):
        for slots in CAPACITIES:
            identifier = run_id(slots, repetition)
            if identifier == reference_id:
                continue
            if projection(identifier) is None:
                submit(identifier, slots, args.evidence)
            digests = save(args.evidence / f"{identifier}.json", wait_for(identifier), slots, repetition)
            if digests != baseline:
                raise ValueError(f"Scientific outputs diverged for {identifier}")
            print(f"Verified {identifier}", flush=True)


if __name__ == "__main__":
    main()
