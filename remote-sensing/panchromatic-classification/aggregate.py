"""Check the fusion result inventory and render the measured case gallery."""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from fusion import CASES, METHODS
from render import render

FIELDS = ("id", "seed", "factor", "interference", "method", "status",
          "edge_rmse", "band_4_rmse", "band_5_rmse", "band_6_rmse", "fixed_iou", "centroid_iou")


def verified_rows(path, case):
    seed, factor, level = CASES[case]
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        if tuple(reader.fieldnames) != FIELDS or {row["method"] for row in rows} != set(METHODS):
            raise ValueError(f"Malformed treatment inventory in {path.name}")
    if len(rows) != len(METHODS):
        raise ValueError(f"Repeated treatment in {path.name}")
    for row in rows:
        if (int(row["id"]), int(row["seed"]), int(row["factor"]), float(row["interference"])) != (
            case, seed, factor, level
        ):
            raise ValueError(f"Result identity mismatch in {path.name}")
        numbers = [float(row[name]) for name in FIELDS[6:]]
        if (row["status"] not in ({"ok", "degenerate"} if row["method"] == "pca" else {"ok"})
                or not all(math.isfinite(value) and value >= 0 for value in numbers)
                or max(numbers[-2:]) > 1):
            raise ValueError(f"Invalid scientific metric in {path.name}")
    return rows


def aggregate(source, output, count):
    paths = sorted(source.glob("case-*.csv"))
    if [path.name for path in paths] != [f"case-{i:03d}.csv" for i in range(count)]:
        raise ValueError("Missing or unexpected case artifacts")
    groups = defaultdict(list)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "scene-metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for case, path in enumerate(paths):
            rows = verified_rows(path, case)
            writer.writerows(rows)
            for row in rows:
                groups[int(row["factor"]), float(row["interference"]), row["method"]].append(row)
    with (output / "condition-summary.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("factor", "interference", "method", "scenes", "degenerate",
                         "median_edge_rmse", "median_fixed_iou", "median_centroid_iou"))
        for key, rows in sorted(groups.items()):
            medians = [np.median([float(row[field]) for row in rows])
                       for field in ("edge_rmse", "fixed_iou", "centroid_iou")]
            writer.writerow((*key, len(rows), sum(row["status"]=="degenerate" for row in rows), *medians))
    models = json.loads((source / "centroids.json").read_text())
    render(output, models, 0, 2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cases", type=int, choices=(48, 768), default=768)
    args = parser.parse_args()
    aggregate(args.source, args.output, args.cases)
