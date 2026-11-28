"""Plot throughput and measured activity overlap from the ngspice profile summary."""

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
    rows = list(csv.DictReader(stream))

slots = [int(row["slots"]) for row in rows]
if slots != [1, 4, 8, 16] or any(int(row["repetitions"]) != 3 for row in rows):
    raise ValueError("Expected three repetitions at each configured slot count")

figure, (throughput, overlap) = plt.subplots(1, 2, figsize=(10, 4.4), layout="constrained")
rates = [float(row["median_circuits_per_second"]) for row in rows]
throughput.plot(slots, rates, "o-", color="#196b58")
throughput.set(title="Median end-to-end throughput", ylabel="Circuits per second", ylim=(0, None))

peak = [int(row["peak_overlapping_batches"]) for row in rows]
overlap.plot(slots, slots, "o--", color="#777777", label="Configured slots")
overlap.plot(slots, peak, "o-", color="#a64b30", label="Peak observed overlap")
overlap.set(title="Concurrent simulation batches", ylabel="Batches", ylim=(0, None))
overlap.legend()

for axis in (throughput, overlap):
    axis.set(xlabel="Configured slots", xticks=slots)
    axis.grid(alpha=0.22)
figure.savefig(args.output, dpi=115)
