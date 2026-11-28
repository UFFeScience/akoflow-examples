"""Plot observed batch concurrency from a captured AkôFlow run."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("capture", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
capture = json.loads(args.capture.read_text())
batches = [activity for activity in capture["activities"] if "-batch-" in activity["activityId"]]
start = min(item["startedAt"] for item in batches)
events = []
for item in batches:
    events.extend(((item["startedAt"] - start, 1), (item["finishedAt"] - start, -1)))
times, counts, active = [0], [0], 0
for instant, delta in sorted(events):
    active += delta
    times.append(instant)
    counts.append(active)

figure, (workers, axis) = plt.subplots(
    2, 1, figsize=(10, 5.4), sharex=True, height_ratios=(2, 1), layout="constrained"
)
resources = sorted({item["allocatedResourceId"] for item in batches})
for level, resource in enumerate(resources):
    intervals = [
        (item["startedAt"] - start, item["finishedAt"] - item["startedAt"])
        for item in batches if item["allocatedResourceId"] == resource
    ]
    workers.broken_barh(intervals, (level - 0.35, 0.7), facecolors="#196b58")
workers.set(title=f"ngspice RLC ensemble · {len(batches)} batches · {capture['slots']} slots",
            ylabel="Worker slot", yticks=range(len(resources)), yticklabels=range(1, len(resources) + 1))
axis.step(times, counts, where="post", color="#196b58", linewidth=1)
axis.fill_between(times, counts, step="post", color="#196b58", alpha=0.2)
axis.set(xlabel="Seconds since the first batch started", ylabel="Active batches",
         ylim=(0, max(counts) + 0.5), yticks=range(max(counts) + 1))
axis.grid(axis="y", alpha=0.2)
figure.savefig(args.output, dpi=115)
