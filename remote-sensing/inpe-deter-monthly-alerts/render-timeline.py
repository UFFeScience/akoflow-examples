"""Plot the measured placement and overlap of the DETER monthly audit tasks."""

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
months = [item for item in capture["activities"] if "-month-" in item["activityId"]]
if len(months) != 72 or any(item["status"] != "completed" for item in months):
    raise ValueError("The timeline requires all 72 monthly activities")
origin = min(item["startedAt"] for item in months)
resources = sorted({item["allocatedResourceId"] for item in months})
colors = ("#286148", "#b36727", "#798f39", "#3e6586", "#914d74", "#8c4637")
figure, (workers, concurrency) = plt.subplots(
    2, 1, figsize=(10, 5.3), sharex=True, height_ratios=(2, 1), layout="constrained"
)
events = []
for level, resource in enumerate(resources):
    for item in months:
        if item["allocatedResourceId"] != resource:
            continue
        start, end = item["startedAt"] - origin, item["finishedAt"] - origin
        year = int(item["activityId"].rsplit("-", 2)[1])
        workers.broken_barh([(start, end - start)], (level - 0.36, 0.72),
                            facecolors=colors[year - 2019])
        events.extend(((start, 1), (end, -1)))
workers.set(title=f"INPE DETER · 72 monthly audits · {capture['slots']} slots", ylabel="Worker slot",
            yticks=range(len(resources)), yticklabels=range(1, len(resources) + 1))
for year, color in enumerate(colors, 2019):
    workers.plot([], [], color=color, linewidth=4, label=year)
workers.legend(ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.13), frameon=False)
times, counts, count = [0], [0], 0
for time, delta in sorted(events):
    count += delta
    times.append(time)
    counts.append(count)
concurrency.step(times, counts, where="post", color="#286148")
concurrency.set(xlabel="Seconds since the first monthly activity started", ylabel="Concurrent audits",
                yticks=range(max(counts) + 1))
concurrency.grid(axis="y", alpha=0.22)
figure.savefig(args.output, dpi=120)
