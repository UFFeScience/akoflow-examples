"""Compare the same 72 DETER partitions across the three scheduling plans."""

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path

CAPACITIES = (1, 4, 8)


def timestamp(value):
    return value if isinstance(value, (float, int)) else datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def measure(capture):
    run = capture["run"]
    if run["status"] != "completed":
        raise ValueError(f"Run {run['id']} is incomplete")
    activities = capture["activities"]
    months = [item for item in activities if "-month-" in item["activityId"]]
    if len(months) != 72 or any(item["status"] != "completed" for item in activities):
        raise ValueError(f"Run {run['id']} lacks its complete month trace")
    prepare, = [item for item in activities if item["activityId"].endswith("-prepare")]
    aggregate, = [item for item in activities if item["activityId"].endswith("-aggregate")]
    return {
        "slots": capture["slots"], "run": run["id"],
        "end_to_end_seconds": timestamp(run["finishedAt"]) - timestamp(run["startedAt"]),
        "post_preparation_seconds": aggregate["finishedAt"] - prepare["finishedAt"],
        "max_overlapping_months": capture["max_overlapping_months"],
        "transferred_bytes": sum(item.get("transferBytes", 0) for item in activities),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    captures = [json.loads(file.read_text()) for file in args.captures.glob("community-inpe-deter-run-*.json")]
    captures.sort(key=lambda item: item["slots"])
    if tuple(item["slots"] for item in captures) != CAPACITIES:
        raise ValueError("Expected one complete run for each of the 1-, 4-, and 8-slot plans")
    if any(item["digests"] != captures[0]["digests"] for item in captures):
        raise ValueError("Scientific results differ across slot counts")
    rows = [measure(item) for item in captures]
    serial = rows[0]["post_preparation_seconds"]
    for row in rows:
        row["post_preparation_speedup"] = serial / row["post_preparation_seconds"]
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
