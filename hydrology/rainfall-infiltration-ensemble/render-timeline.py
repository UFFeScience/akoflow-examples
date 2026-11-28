"""Plot batch activity overlap and color each task by its observed ponding fraction."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("batch_summary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    capture = json.loads(args.capture.read_text())
    with args.batch_summary.open(newline="") as stream:
        fractions = {row["id"]: float(row["ponded_fraction"]) for row in csv.DictReader(stream)}
    batches = [item for item in capture["activities"] if "-batch-" in item["activityId"]]
    identifiers = {f"batch-{item['activityId'].rsplit('-', 1)[1]}" for item in batches}
    if len(batches) != 512 or identifiers != fractions.keys():
        raise ValueError("Timeline and results must contain the same 512 batches")
    start = min(item["startedAt"] for item in batches)
    observed_resources = sorted({item["allocatedResourceId"] for item in batches})
    levels = {resource: level for level, resource in enumerate(observed_resources)}
    figure, (workers, concurrency) = plt.subplots(
        2, 1, figsize=(12, 6.6), sharex=True, height_ratios=(3, 1), layout="constrained"
    )
    colors = plt.get_cmap("viridis")
    events = []
    for item in batches:
        first, last = item["startedAt"] - start, item["finishedAt"] - start
        level = levels[item["allocatedResourceId"]]
        key = f"batch-{item['activityId'].rsplit('-', 1)[1]}"
        workers.broken_barh([(first, last - first)], (level - 0.4, 0.8),
                            facecolors=colors(fractions[key]), linewidth=0)
        events.extend(((first, 1), (last, -1)))
    mapper = ScalarMappable(norm=Normalize(0, 1), cmap=colors)
    figure.colorbar(mapper, ax=workers, label="Fraction of columns ponded")
    workers.set(title=f"Rainfall infiltration · {capture['slots']} configured slots",
                ylabel="Worker slot", yticks=range(len(levels)),
                yticklabels=range(1, len(levels) + 1))
    times, counts, active = [0], [0], 0
    for instant, delta in sorted(events):
        active += delta
        times.append(instant)
        counts.append(active)
    concurrency.step(times, counts, where="post", color="#196b58")
    concurrency.set(xlabel="Seconds since the first batch started", ylabel="Active batches")
    figure.savefig(args.output, dpi=115)


if __name__ == "__main__":
    main()
