"""Run five LBM shear-wave scheduling profiles sequentially and capture evidence."""

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

from generate import ACTIVITIES, BATCHES, CAPACITIES, PREFIX, WORKFLOW

ROOT = Path(__file__).resolve().parent
API = os.environ.get("AKOFLOW_API_URL", "http://127.0.0.1:8080/akoflow-api").rstrip("/")
TOKEN = os.environ.get("AKOFLOW_API_TOKEN", "akoflow-development-token")
DETERMINISTIC = ("amplitudes.csv.gz", "case-metrics.csv", "shear-space-time.png", "shear-decay.gif", "validation.json")


def seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(value).timestamp()


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
    return f"{PREFIX}-run-{slots}-v1" + (f"-r{repetition}" if repetition > 1 else "")


def check_manifest(result):
    flow = result["activities"]
    expected = {f"{WORKFLOW}-{name}" for name in ACTIVITIES}
    if len(flow) != len(expected) or {item["activityId"] for item in flow} != expected:
        raise ValueError("Unexpected activity inventory")
    if any(item["status"] != "completed" for item in flow):
        raise ValueError("An activity did not complete")
    paths = {f"{name}-{kind}.csv" for name in BATCHES for kind in ("trace", "metrics")}
    paths.add("case-127-field.csv")
    observed = Counter(item["relativePath"] for item in result["dataObjects"]
                       if item["relativePath"] in paths)
    if observed != Counter(paths):
        raise ValueError("Missing or repeated case artifact")
    artifacts = [item for item in result["dataObjects"] if item["relativePath"] in DETERMINISTIC]
    digests = {item["relativePath"]: item["checksum"] for item in artifacts}
    if len(artifacts) != len(DETERMINISTIC) or set(digests) != set(DETERMINISTIC):
        raise ValueError("Missing or repeated aggregate output")
    if any(not digest for digest in digests.values()):
        raise ValueError("Missing aggregate output checksum")
    return digests


def save(path, result, slots, repetition, baseline=None):
    digests = check_manifest(result)
    if baseline is not None and digests != baseline:
        raise ValueError(f"Scientific outputs diverged for {path.stem}")
    flow = result["activities"]
    case_ids = {f"{WORKFLOW}-{name}" for name in BATCHES[:-1]}
    scientific = [item for item in flow if item["activityId"] in case_ids]
    aggregate = next(item for item in flow if item["activityId"] == f"{WORKFLOW}-aggregate")
    if any(not item.get("startedAt") or not item.get("finishedAt") for item in flow):
        raise ValueError("Missing activity timestamps")
    intervals = [(seconds(item["startedAt"]), seconds(item["finishedAt"])) for item in scientific]
    aggregate_start = seconds(aggregate["startedAt"])
    if any(seconds(item["finishedAt"]) > aggregate_start for item in flow if item is not aggregate):
        raise ValueError("Aggregation began before a predecessor finished")
    valid = [(started, finished) for started, finished in intervals if 0 < started < finished]
    changes = Counter(started for started, _ in valid)
    changes.subtract(finished for _, finished in valid)
    active = peak = 0
    for timestamp in sorted(changes):
        active += changes[timestamp]
        peak = max(peak, active)
    if not 1 <= peak <= slots:
        raise ValueError(f"Observed peak {peak} is incompatible with {slots} slots")
    run = result["run"]
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({
        "slots": slots, "repetition": repetition,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "run": run, "activities": flow, "max_overlapping_batches": peak,
        "unusable_case_intervals": len(intervals) - len(valid),
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
                       AKOFLOW_PLAN_ID=f"{PREFIX}-plan-{slots}-v1", AKOFLOW_SUBMIT="1")
    with (directory / f"{identifier}.log").open("a") as log:
        subprocess.run([ROOT / "run.sh"], env=command_env, stdout=log, stderr=log, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--repetitions", type=int, choices=range(1, 11), default=1)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    # Reuse the initial four-slot run before submitting any additional profile.
    reference_id = run_id(4, 1)
    if projection(reference_id) is None:
        submit(reference_id, 4, args.evidence)
    baseline = save(args.evidence / f"{reference_id}.json", wait_for(reference_id), 4, 1)
    print(f"Verified {reference_id}", flush=True)
    for repetition in range(1, args.repetitions + 1):
        for slots in CAPACITIES:
            identifier = run_id(slots, repetition)
            if identifier == reference_id:
                continue
            if projection(identifier) is None:
                submit(identifier, slots, args.evidence)
            save(args.evidence / f"{identifier}.json", wait_for(identifier), slots, repetition, baseline)
            print(f"Verified {identifier}", flush=True)


if __name__ == "__main__":
    main()
