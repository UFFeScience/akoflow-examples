"""Render measured IDW block occupancy from a completed profile capture."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import Patch

from generate import BATCHES, WORKFLOW


def render(capture, output):
    prefix = f"{WORKFLOW}-"
    expected = {f"{prefix}{block}" for block in BATCHES}
    activities = [task for task in capture["activities"] if task["activityId"] in expected]
    if (capture["run"]["status"] != "completed" or len(activities) != len(expected)
            or {task["activityId"] for task in activities} != expected
            or any(task["status"] != "completed" or not 0 < task["startedAt"] < task["finishedAt"]
                   for task in activities)):
        raise ValueError("Expected a completed timing trace for all 1,024 prediction blocks")

    first = min(task["startedAt"] for task in activities)
    resources = sorted({task["allocatedResourceId"] for task in activities})
    slots = {resource: index for index, resource in enumerate(resources)}
    colors = {"raw": "#286581", "filtered": "#a75a2a"}
    intervals = defaultdict(list)
    deltas = defaultdict(int)
    for task in activities:
        start, finish = task["startedAt"] - first, task["finishedAt"] - first
        condition = task["activityId"].removeprefix(prefix).split("-")[1]
        intervals[slots[task["allocatedResourceId"]], condition].append((start, finish - start))
        deltas[start] += 1
        deltas[finish] -= 1

    figure, (workers, concurrency) = plt.subplots(
        2, 1, figsize=(12, 6), sharex=True, height_ratios=(3, 1), layout="constrained",
    )
    for (slot, condition), segments in intervals.items():
        workers.broken_barh(segments, (slot - 0.35, 0.7), facecolors=colors[condition], linewidth=0)
    workers.set(title=f"Synthetic IDW · {capture['slots']} configured slots",
                ylabel="Observed worker slot")
    if len(resources) <= 16:
        workers.set_yticks(range(len(resources)), [str(i + 1) for i in range(len(resources))])
    workers.legend(handles=[Patch(color=color, label=condition.capitalize())
                            for condition, color in colors.items()], loc="upper left")
    times, counts, count = [], [], 0
    for instant, delta in sorted(deltas.items()):
        count += delta
        times.append(instant)
        counts.append(count)
    if max(counts) != capture["max_overlapping_batches"] or count != 0:
        raise ValueError("Timeline does not reproduce the captured peak concurrency")
    concurrency.step(times, counts, where="post", color="#245b48")
    concurrency.set(xlabel="Seconds since the first prediction block started",
                    ylabel="Active blocks", ylim=(0, max(counts) + 0.5))
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=120)
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(json.loads(args.capture.read_bytes()), args.output)
