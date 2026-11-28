"""Summarize completed synthetic IDW profiling runs without mixing timing scopes."""

import argparse
import csv
import json
import statistics
from datetime import datetime
from pathlib import Path

from generate import BATCHES, CAPACITIES, PREPARATIONS


def seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def shared_host_seconds(run, neighbors):
    """Union of completed neighboring run windows intersecting this run."""
    start, end = seconds(run["startedAt"]), seconds(run["finishedAt"])
    overlaps = []
    for other in neighbors:
        if other["id"] == run["id"]:
            continue
        first = max(start, seconds(other["startedAt"]))
        last = min(end, seconds(other["finishedAt"]))
        if first < last:
            overlaps.append((first, last))
    seconds_shared, covered_until = 0.0, start
    for first, last in sorted(overlaps):
        seconds_shared += max(0.0, last - max(first, covered_until))
        covered_until = max(covered_until, last)
    return seconds_shared


def measure(capture):
    run = capture["run"]
    if run["status"] != "completed":
        raise ValueError(f"Run {run['id']} is incomplete")
    batches = [item for item in capture["activities"] if "-block-" in item["activityId"]]
    if len(batches) != len(BATCHES):
        raise ValueError(f"Run {run['id']} lacks its complete batch trace")
    prep = [item for item in capture["activities"] if "-prepare-" in item["activityId"]]
    if len(prep) != len(PREPARATIONS):
        raise ValueError(f"Run {run['id']} lacks its complete preparation trace")
    reducer, = [item for item in capture["activities"] if item["activityId"].endswith("-aggregate")]
    latencies = [item["startedAt"] - item["readyAt"] for item in batches]
    if any(item["readyAt"] <= 0 for item in batches) or min(latencies) < 0:
        raise ValueError(f"Invalid ready-to-start timestamps in {run['id']}")
    makespan = seconds(run["finishedAt"]) - seconds(run["startedAt"])
    window = seconds(reducer["finishedAt"]) - max(seconds(item["finishedAt"]) for item in prep)
    artifact_bytes = sum(item["sizeBytes"] for item in capture["artifacts"])
    response_bytes = sum(item["sizeBytes"] for item in capture["artifacts"]
                         if "-block-" in item["relativePath"])
    return {
        "run": run["id"], "slots": capture["slots"], "repetition": capture["repetition"],
        "end_to_end_seconds": makespan, "blocks_per_second": len(BATCHES) / makespan,
        "post_preparation_seconds": window,
        "artifact_bytes": artifact_bytes, "batch_result_bytes": response_bytes,
        "batch_window_seconds": max(item["finishedAt"] for item in batches)
        - min(item["startedAt"] for item in batches),
        "median_ready_to_start_seconds": statistics.median(latencies),
        "median_batch_seconds": statistics.median(item["finishedAt"] - item["startedAt"] for item in batches),
        "completion_tail_seconds": max(item["finishedAt"] for item in batches)
        - statistics.median(item["finishedAt"] for item in batches),
        "max_overlapping_batches": capture["max_overlapping_batches"],
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
    parser.add_argument("--shared-host-captures", type=Path, action="append", default=[],
                        help="Directory of completed neighboring benchmark captures; repeat as needed")
    parser.add_argument("--repetitions", type=int, choices=range(1, 11), default=1)
    args = parser.parse_args()
    captures = [json.loads(path.read_text()) for path in sorted(args.captures.glob("community-synthetic-idw-run-*.json"))]
    if len(captures) != len(CAPACITIES) * args.repetitions:
        raise ValueError("Expected a complete set of profile captures")
    reference = captures[0]["digests"]
    if any(item["digests"] != reference for item in captures):
        raise ValueError("Profile outputs differ")
    runs = [measure(item) for item in captures]
    if args.shared_host_captures:
        neighbors = []
        for directory in args.shared_host_captures:
            for path in sorted(directory.glob("*.json")):
                neighbor = json.loads(path.read_text())["run"]
                if neighbor["status"] != "completed":
                    raise ValueError(f"Expected a completed neighboring capture at {path}")
                neighbors.append(neighbor)
        for row, capture in zip(runs, captures):
            row["shared_host_seconds"] = shared_host_seconds(capture["run"], neighbors)
    if {(row["slots"], row["repetition"]) for row in runs} != {
        (slots, repetition) for slots in CAPACITIES for repetition in range(1, args.repetitions + 1)
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
            "median_blocks_per_second": statistics.median(row["blocks_per_second"] for row in group),
            "median_post_preparation_seconds": comparable,
            "post_preparation_speedup": serial/comparable,
            "median_artifact_bytes": statistics.median(row["artifact_bytes"] for row in group),
            "median_batch_result_bytes": statistics.median(row["batch_result_bytes"] for row in group),
            "median_ready_to_start_seconds": statistics.median(
                row["median_ready_to_start_seconds"] for row in group),
            "median_completion_tail_seconds": statistics.median(row["completion_tail_seconds"] for row in group),
            "peak_overlapping_batches": max(row["max_overlapping_batches"] for row in group),
        })
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "profile-runs.csv", runs)
    write_csv(args.output / "profile-summary.csv", summaries)


if __name__ == "__main__":
    main()
