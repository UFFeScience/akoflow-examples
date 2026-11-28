"""Summarize completed Sobol profiling runs without mixing timing scopes."""

import argparse
import csv
import json
import statistics
from datetime import datetime
from pathlib import Path

CAPACITIES = (1, 4, 8, 16)


def seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def measure(capture):
    run = capture["run"]
    if run["status"] != "completed":
        raise ValueError(f"Run {run['id']} is incomplete")
    replicas = [item for item in capture["activities"] if "-replicate-" in item["activityId"]]
    if len(replicas) != 128:
        raise ValueError(f"Run {run['id']} lacks its complete replicate trace")
    prep, = [item for item in capture["activities"] if item["activityId"].endswith("-prepare")]
    reducer, = [item for item in capture["activities"] if item["activityId"].endswith("-aggregate")]
    makespan = seconds(run["finishedAt"]) - seconds(run["startedAt"])
    window = seconds(reducer["finishedAt"]) - seconds(prep["finishedAt"])
    return {
        "run": run["id"], "slots": capture["slots"], "repetition": capture["repetition"],
        "end_to_end_seconds": makespan, "post_preparation_seconds": window,
        "replicate_window_seconds": max(item["finishedAt"] for item in replicas)
        - min(item["startedAt"] for item in replicas),
        "median_queue_seconds": statistics.median(item.get("queueSeconds", 0) for item in replicas),
        "median_replica_seconds": statistics.median(item["finishedAt"] - item["startedAt"] for item in replicas),
        "max_overlapping_replicates": capture["max_overlapping_replicates"],
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
    args = parser.parse_args()
    captures = [json.loads(path.read_text()) for path in sorted(args.captures.glob("community-sobol-run-*.json"))]
    if len(captures) != 12:
        raise ValueError("Expected twelve completed profile captures")
    reference = captures[0]["digests"]
    if any(item["digests"] != reference for item in captures):
        raise ValueError("Profile outputs differ")
    runs = [measure(item) for item in captures]
    if {(row["slots"], row["repetition"]) for row in runs} != {
        (slots, repetition) for slots in CAPACITIES for repetition in (1, 2, 3)
    }:
        raise ValueError("Profiles are missing a repetition")
    serial = statistics.median(row["post_preparation_seconds"] for row in runs if row["slots"] == 1)
    summaries = []
    for slots in CAPACITIES:
        group = [row for row in runs if row["slots"] == slots]
        comparable = statistics.median(row["post_preparation_seconds"] for row in group)
        summaries.append({
            "slots": slots, "repetitions": len(group),
            "median_end_to_end_seconds": statistics.median(row["end_to_end_seconds"] for row in group),
            "median_post_preparation_seconds": comparable,
            "post_preparation_speedup": serial/comparable,
            "peak_overlapping_replicates": max(row["max_overlapping_replicates"] for row in group),
        })
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "profile-runs.csv", runs)
    write_csv(args.output / "profile-summary.csv", summaries)


if __name__ == "__main__":
    main()
