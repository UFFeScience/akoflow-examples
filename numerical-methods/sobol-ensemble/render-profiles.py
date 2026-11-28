"""Render measured Sobol scheduling results from the profile summary CSV."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("summary", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
with args.summary.open(newline="") as stream:
    data = list(csv.DictReader(stream))
slots = [int(row["slots"]) for row in data]
if slots != [1, 4, 8, 16] or any(int(row["repetitions"]) != 3 for row in data):
    raise ValueError("The profile figure requires three repetitions per capacity")

figure, (duration, concurrency) = plt.subplots(1, 2, figsize=(10, 4.4), layout="constrained")
colors = ("#196b58", "#a64b30")
for field, label, color in zip(
    ("median_end_to_end_seconds", "median_post_preparation_seconds"),
    ("End to end", "After preparation"), colors,
):
    duration.plot(slots, [float(row[field]) for row in data], "o-", color=color, label=label)
duration.set(title="Median workflow duration", xlabel="Configured slots", ylabel="Seconds", xticks=slots)
duration.legend()

measured = [int(row["peak_overlapping_replicates"]) for row in data]
concurrency.plot(slots, slots, "o--", color="#777777", label="Configured slots")
concurrency.plot(slots, measured, "o-", color=colors[0], label="Peak measured overlap")
concurrency.set(title="Concurrent replica activities", xlabel="Configured slots",
                ylabel="Replicas", xticks=slots)
concurrency.legend()
for axis in (duration, concurrency):
    axis.grid(alpha=0.22)
figure.savefig(args.output, dpi=115)
