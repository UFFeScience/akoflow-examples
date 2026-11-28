"""Compare completed LBM scheduling profiles against their one-slot controls."""

import argparse
import csv
import json
import statistics
from pathlib import Path

from generate import BATCHES, CAPACITIES, WORKFLOW
from profile import DETERMINISTIC, run_id, seconds


def measure(capture):
    run = capture["run"]
    flow = capture["activities"]
    if run["status"] != "completed" or any(item["status"] != "completed" for item in flow):
        raise ValueError(f"Run {run['id']} is incomplete")
    by_id = {item["activityId"]: item for item in flow}
    cases = [by_id[f"{WORKFLOW}-{name}"] for name in BATCHES[:-1]]
    valid = [item for item in cases if 0 < seconds(item["startedAt"]) < seconds(item["finishedAt"])]
    missing = len(cases) - len(valid)
    if not valid or missing != capture.get("unusable_case_intervals", 0):
        raise ValueError(f"Unexpected number of unusable case intervals in {run['id']}")
    reducer = by_id[f"{WORKFLOW}-aggregate"]
    elapsed = seconds(run["finishedAt"]) - seconds(run["startedAt"])
    if elapsed <= 0:
        raise ValueError(f"Invalid elapsed time in {run['id']}")
    return {
        "run": run["id"],
        "slots": capture["slots"],
        "repetition": capture["repetition"],
        "end_to_end_seconds": elapsed,
        "cases_per_second": len(cases) / elapsed,
        "case_window_seconds": max(seconds(item["finishedAt"]) for item in valid)
        - min(seconds(item["startedAt"]) for item in valid),
        "unusable_case_intervals": missing,
        "aggregate_seconds": seconds(reducer["finishedAt"]) - seconds(reducer["startedAt"]),
        "peak_overlapping_cases": capture["max_overlapping_batches"],
    }


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--repetitions", type=int, choices=range(1, 11), default=1)
    args = parser.parse_args()
    runs = []
    reference = None
    for repetition in range(1, args.repetitions + 1):
        for slots in CAPACITIES:
            identifier = run_id(slots, repetition)
            path = args.captures / f"{identifier}.json"
            capture = json.loads(path.read_text())
            if (capture["run"]["id"], capture["slots"], capture["repetition"]) != (
                identifier, slots, repetition
            ):
                raise ValueError(f"Capture does not match {path.name}")
            digests = capture["digests"]
            if set(digests) != set(DETERMINISTIC) or not all(digests.values()):
                raise ValueError(f"Incomplete result digests in {path.name}")
            if reference is None:
                reference = digests
            if digests != reference:
                raise ValueError(f"Result digests differ in {path.name}")
            runs.append(measure(capture))
    serial = statistics.median(row["end_to_end_seconds"] for row in runs if row["slots"] == 1)
    summaries = []
    for slots in CAPACITIES:
        group = [row for row in runs if row["slots"] == slots]
        elapsed = statistics.median(row["end_to_end_seconds"] for row in group)
        summaries.append({
            "slots": slots,
            "repetitions": len(group),
            "median_end_to_end_seconds": elapsed,
            "speedup_over_one_slot": serial / elapsed,
            "median_case_window_seconds": statistics.median(row["case_window_seconds"] for row in group),
            "median_aggregate_seconds": statistics.median(row["aggregate_seconds"] for row in group),
            "peak_overlapping_cases": max(row["peak_overlapping_cases"] for row in group),
            "unusable_case_intervals": sum(row["unusable_case_intervals"] for row in group),
        })
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "profile-runs.csv", runs)
    write_csv(args.output / "profile-summary.csv", summaries)


if __name__ == "__main__":
    main()
