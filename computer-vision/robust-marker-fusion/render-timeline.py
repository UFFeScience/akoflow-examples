"""Render measured scenario occupancy by worker from a scheduling profile."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt


def render(report, output):
    intervals = report["case_intervals"]
    first = min(interval["start"] for interval in intervals)
    worker_segments = defaultdict(list)
    events = Counter()
    for interval in intervals:
        start, end = interval["start"] - first, interval["end"] - first
        worker_segments[interval["worker"]].append((start, end - start))
        events[start] += 1
        events[end] -= 1
    aggregation_start, aggregation_end = [value - first for value in report["aggregation_interval"]]
    if not max(events) <= aggregation_start < aggregation_end:
        raise ValueError("Aggregation must follow the recorded scenario intervals")
    times, counts = [], []
    active = 0
    for instant in sorted(events):
        active += events[instant]
        times.append(instant)
        counts.append(active)
    if active != 0 or max(counts) != report["peak_overlap_lower_bound"]:
        raise ValueError("Recorded overlap does not match the worker timeline")

    figure, (workers, overlap) = plt.subplots(
        2, 1, figsize=(11, 6), sharex=True, height_ratios=(3, 1), layout="constrained"
    )
    for index, worker in enumerate(sorted(worker_segments)):
        workers.broken_barh(worker_segments[worker], (index - 0.35, 0.7), facecolors="#286581")
    workers.set(title=f"Robust marker fusion · {report['slots']} configured slots",
                ylabel="Worker slot")
    workers.set_yticks(range(len(worker_segments)), range(1, len(worker_segments) + 1))
    if report["unusable_case_intervals"]:
        workers.text(.99, .97, f"{report['unusable_case_intervals']} unavailable intervals",
                     transform=workers.transAxes, ha="right", va="top")
    overlap.step([*times, aggregation_end], [*counts, 0], where="post", color="#245b48")
    overlap.set(xlabel="Seconds since first recorded scenario", ylabel="Active cases")
    for axis in (workers, overlap):
        axis.axvspan(aggregation_start, aggregation_end, color="#e5a65e", alpha=.35)
        axis.grid(axis="x", alpha=.2)
    figure.savefig(output, dpi=120)
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(json.loads(args.profile.read_bytes()), args.output)
