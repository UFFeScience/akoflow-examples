"""Validate and aggregate the registered sequence results."""

import argparse
import csv
import gzip
import io
from collections import defaultdict
from pathlib import Path

import numpy as np

from render import render
from stabilize import CASES, FRAMES, REGIMES

METHODS = ("unregistered", "cross-anchored", "cross-chained",
           "phase-anchored", "phase-chained")
FIELDS = ("frame", "method", "status", "alignment_y", "alignment_x",
          "peak_ratio", "trajectory_error_px", "truth_y", "truth_x",
          "common_mae", "common_pixels")


def validate(path):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {(frame, method) for frame in range(FRAMES) for method in METHODS}
    if len(rows) != len(expected) or {(int(row["frame"]), row["method"]) for row in rows} != expected:
        raise ValueError(f"Incomplete frame inventory in {path.name}")
    for row in rows:
        if row["status"] not in {"ok", "ambiguous", "unavailable"}:
            raise ValueError(f"Unexpected result state in {path.name}")
        vector = np.array([float(row["alignment_y"]), float(row["alignment_x"])])
        truth = np.array([float(row["truth_y"]), float(row["truth_x"])])
        error = float(row["trajectory_error_px"])
        if row["status"] == "ok":
            if not np.isclose(np.linalg.norm(vector + truth), error, rtol=0, atol=1e-10):
                raise ValueError(f"Trajectory error mismatch in {path.name}")
        elif np.isfinite(error) or np.isfinite(vector).any():
            raise ValueError(f"Absent result includes an estimate in {path.name}")
    return rows


def aggregate(source, output, count):
    paths = sorted(source.glob("case-*.csv"))
    if [path.name for path in paths] != [f"case-{i:03d}.csv" for i in range(count)]:
        raise ValueError("Missing or unexpected case artifacts")
    groups = defaultdict(list)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "sequence-metrics.csv.gz").open("wb") as file:
        with gzip.GzipFile(fileobj=file, mode="wb", filename="", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=("case", "seed", "amplitude", "regime", *FIELDS),
                                        lineterminator="\n")
                writer.writeheader()
                for case, path in enumerate(paths):
                    seed, amplitude, regime = CASES[case]
                    regime_index = REGIMES.index(regime)
                    for row in validate(path):
                        writer.writerow(dict(case=case, seed=seed, amplitude=amplitude,
                                             regime=regime_index, **row))
                        if int(row["frame"]) == FRAMES - 1:
                            groups[amplitude, regime_index, row["method"]].append(row)
    with (output / "condition-summary.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("amplitude", "regime", "method", "cases", "available", "median_error_px",
                         "p90_error_px", "median_common_mae"))
        for (amplitude, regime, method), rows in sorted(groups.items()):
            errors = [float(row["trajectory_error_px"]) for row in rows if row["status"] == "ok"]
            maes = [float(row["common_mae"]) for row in rows if int(row["common_pixels"]) > 0]
            writer.writerow((amplitude, regime, method, len(rows), len(errors),
                             np.median(errors) if errors else "", np.quantile(errors, .9) if errors else "",
                             np.median(maes) if maes else ""))
    render(11, paths[11], output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cases", type=int, choices=(48, 768), default=768)
    args = parser.parse_args()
    aggregate(args.source, args.output, args.cases)
