"""Render measured microscopy sequence occupancy from a completed profile capture."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import Patch

from generate import PREFIX
from stabilize import CASES, REGIMES


def render(capture, output):
    count = capture["cases"]
    workflow = f"{PREFIX}-{'ensemble' if count == 768 else 'profile'}-v1"
    prefix = f"{workflow}-case-"
    expected = {f"{prefix}{case:03d}" for case in range(count)}
    activities = [task for task in capture["activities"] if task["activityId"] in expected]
    if (capture["run"]["status"] != "completed" or len(activities) != len(expected)
            or {task["activityId"] for task in activities} != expected
            or any(task["status"] != "completed" or not 0 < task["startedAt"] < task["finishedAt"]
                   for task in activities)):
        raise ValueError("Expected a completed timing trace for each sequence")

    first = min(task["startedAt"] for task in activities)
    resources = sorted({task["allocatedResourceId"] for task in activities})
    slots = {resource: index for index, resource in enumerate(resources)}
    colors = {"Clean": "#286581", "Moderate interference": "#a75a2a",
              "Strong interference": "#52784e"}
    conditions = list(colors)
    intervals = defaultdict(list)
    deltas = defaultdict(int)
    for task in activities:
        start, finish = task["startedAt"] - first, task["finishedAt"] - first
        case = int(task["activityId"].removeprefix(prefix))
        condition = conditions[REGIMES.index(CASES[case][2])]
        intervals[slots[task["allocatedResourceId"]], condition].append((start, finish - start))
        deltas[start] += 1
        deltas[finish] -= 1

    figure, (workers, concurrency) = plt.subplots(
        2, 1, figsize=(12, 6), sharex=True, height_ratios=(3, 1), layout="constrained",
    )
    for (slot, condition), segments in intervals.items():
        workers.broken_barh(segments, (slot - 0.35, 0.7), facecolors=colors[condition], linewidth=0)
    workers.set(title=f"Microscopy stabilization · {capture['slots']} configured slots",
                ylabel="Observed worker slot")
    if len(resources) <= 16:
        workers.set_yticks(range(len(resources)), [str(i + 1) for i in range(len(resources))])
    handles = [Patch(color=color, label=condition) for condition, color in colors.items()]
    handles.append(Patch(color="#b1b1bb", alpha=0.45, label="Aggregation"))
    workers.legend(handles=handles, loc="upper right")
    times, counts, count = [], [], 0
    for instant, delta in sorted(deltas.items()):
        count += delta
        times.append(instant)
        counts.append(count)
    if max(counts) != capture["peak_overlapping_cases"] or count != 0:
        raise ValueError("Timeline does not reproduce the captured peak concurrency")
    reducer, = [task for task in capture["activities"] if task["activityId"] == f"{workflow}-aggregate"]
    start, end = reducer["startedAt"] - first, reducer["finishedAt"] - first
    if start < max(times) or end <= start:
        raise ValueError("Unexpected aggregation timing")
    for axis in (workers, concurrency):
        axis.axvspan(start, end, color="#b1b1bb", alpha=0.45)
    concurrency.step([*times, end], [*counts, 0], where="post", color="#245b48")
    concurrency.set(xlabel="Seconds since the first sequence started",
                    ylabel="Active sequences", ylim=(0, max(counts) + 0.5))
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=120)
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(json.loads(args.capture.read_bytes()), args.output)
