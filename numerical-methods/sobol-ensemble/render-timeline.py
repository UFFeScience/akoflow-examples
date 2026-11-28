"""Plot observed replicate concurrency from a captured AkôFlow run."""

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
replicates = [activity for activity in capture["activities"] if "-replicate-" in activity["activityId"]]
start = min(item["startedAt"] for item in replicates)
events = []
for item in replicates:
    events.extend(((item["startedAt"] - start, 1), (item["finishedAt"] - start, -1)))
times, counts, active = [0], [0], 0
for instant, delta in sorted(events):
    active += delta
    times.append(instant)
    counts.append(active)

figure, axis = plt.subplots(figsize=(10, 4.2), layout="constrained")
axis.step(times, counts, where="post", color="#196b58", linewidth=1)
axis.fill_between(times, counts, step="post", color="#196b58", alpha=0.2)
axis.set(title=f"Sobol ensemble · {len(replicates)} replicas · {capture['slots']} slots",
         xlabel="Seconds since the first replica started", ylabel="Simultaneous replicas",
         ylim=(0, max(counts) + 0.5), yticks=range(max(counts) + 1))
axis.grid(axis="y", alpha=0.2)
figure.savefig(args.output, dpi=115)
