"""Render measured LBM case occupancy from a completed profile capture."""

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import Patch

from generate import BATCHES, ROOT, WORKFLOW
from profile import seconds


def render(capture, output):
    prefix = f"{WORKFLOW}-"
    expected = {f"{prefix}{case}" for case in BATCHES[:-1]}
    activities = [task for task in capture["activities"] if task["activityId"] in expected]
    if (capture["run"]["status"] != "completed" or len(activities) != len(expected)
            or {task["activityId"] for task in activities} != expected
            or any(task["status"] != "completed" for task in activities)):
        raise ValueError("Expected a completed timing trace for all 1,024 scientific cases")
    valid = [task for task in activities if 0 < seconds(task["startedAt"]) < seconds(task["finishedAt"])]
    missing = len(activities) - len(valid)
    if not valid or missing != capture.get("unusable_case_intervals", 0):
        raise ValueError("Unexpected number of unusable case intervals")
    activities = valid

    with (ROOT / "evidence/scenarios.csv").open(newline="") as stream:
        sizes = {row["id"]: int(row["size"]) for row in csv.DictReader(stream)}
    reducer, = [task for task in capture["activities"] if task["activityId"] == f"{WORKFLOW}-aggregate"]
    first = min(seconds(task["startedAt"]) for task in activities)
    resources = sorted({task["allocatedResourceId"] for task in activities})
    slots = {resource: index for index, resource in enumerate(resources)}
    colors = {"Small lattice": "#286581", "Large lattice": "#a75a2a"}
    intervals = defaultdict(list)
    deltas = defaultdict(int)
    for task in activities:
        start = seconds(task["startedAt"]) - first
        finish = seconds(task["finishedAt"]) - first
        case = task["activityId"].removeprefix(f"{prefix}case-")
        condition = "Small lattice" if sizes[case] <= 144 else "Large lattice"
        intervals[slots[task["allocatedResourceId"]], condition].append((start, finish - start))
        deltas[start] += 1
        deltas[finish] -= 1

    figure, (workers, concurrency) = plt.subplots(
        2, 1, figsize=(12, 6), sharex=True, height_ratios=(3, 1), layout="constrained",
    )
    for (slot, condition), segments in intervals.items():
        workers.broken_barh(segments, (slot - 0.35, 0.7), facecolors=colors[condition], linewidth=0)
    workers.set(title=f"LBM shear-wave decay · {capture['slots']} configured slots",
                ylabel="Observed worker slot",
                xlabel=f"Aggregation shaded | {missing} unusable case intervals omitted")
    if len(resources) <= 16:
        workers.set_yticks(range(len(resources)), [str(i + 1) for i in range(len(resources))])
    workers.legend(handles=[Patch(color=color, label=condition)
                            for condition, color in colors.items()], loc="upper left")
    times, counts, count = [], [], 0
    for instant, delta in sorted(deltas.items()):
        count += delta
        times.append(instant)
        counts.append(count)
    if max(counts) != capture["max_overlapping_batches"] or count != 0:
        raise ValueError("Timeline does not reproduce the captured peak concurrency")
    reduce_start = seconds(reducer["startedAt"]) - first
    reduce_end = seconds(reducer["finishedAt"]) - first
    if reduce_start < max(times) or reduce_end <= reduce_start:
        raise ValueError("Unexpected aggregation timing")
    for axis in (workers, concurrency):
        axis.axvspan(reduce_start, reduce_end, color="#b1b1bb", alpha=0.45)
    concurrency.step([*times, reduce_end], [*counts, 0], where="post", color="#245b48")
    concurrency.set(xlabel="Seconds since the first scientific case started",
                    ylabel="Observed active cases", ylim=(0, max(counts) + 0.5))
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=120)
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(json.loads(args.capture.read_bytes()), args.output)
