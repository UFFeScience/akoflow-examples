"""Export per-frame estimates and verify the full marker-fusion inventory."""

import argparse
import csv
import math
from pathlib import Path

from fusion import CASES, MARKERS, estimate, scenario
from render import render

FIELDS = ("case", "frame", "visible_mask", "visible_count", "truth_x", "truth_y",
          "mean_x", "mean_y", "mean_error", "median_x", "median_y", "median_error")


def write_case(case, frames, path):
    truth, orientation, observations, visible = scenario(case, frames)
    count, mean, median = estimate(observations, orientation, visible)
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        for frame in range(frames):
            mask = "".join("1" if value else "0" for value in visible[frame])
            row = [case, frame, mask, count[frame], *truth[frame]]
            for candidate in (mean[frame], median[frame]):
                row.extend((*candidate, math.dist(candidate, truth[frame])) if count[frame]
                           else ("", "", ""))
            writer.writerow(row)


def scene_rows(source, case, frames):
    with (source / f"case-{case:03d}.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(f"Unexpected schema for case {case}")
        rows = list(reader)
    if len(rows) != frames:
        raise ValueError(f"Unexpected frame count for case {case}")
    expected_count = len(MARKERS) - CASES[case][1]
    for frame, row in enumerate(rows):
        mask = row["visible_mask"]
        if (int(row["case"]) != case or int(row["frame"]) != frame
                or len(mask) != len(MARKERS) or set(mask) - {"0", "1"}
                or mask.count("1") != expected_count or int(row["visible_count"]) != expected_count):
            raise ValueError(f"Invalid reference or visibility for case {case}, frame {frame}")
        truth = (float(row["truth_x"]), float(row["truth_y"]))
        if not all(map(math.isfinite, truth)):
            raise ValueError(f"Invalid truth for case {case}, frame {frame}")
        for method in ("mean", "median"):
            values = [row[f"{method}_{field}"] for field in ("x", "y", "error")]
            if expected_count:
                x, y, error = map(float, values)
                if not math.isclose(error, math.dist((x, y), truth), abs_tol=1e-12):
                    raise ValueError(f"Invalid error for case {case}, frame {frame}")
            elif any(values):
                raise ValueError(f"Unexpected estimate for case {case}, frame {frame}")
    return rows


def summarize(source, frames, output):
    expected = {f"case-{case:03d}.csv" for case in range(len(CASES))}
    if {path.name for path in source.glob("case-*.csv")} != expected:
        raise ValueError("Missing or unexpected scenario CSVs")
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("case", "seed", "hidden", "bias", "available_frames", "mean_rmse", "median_rmse"))
        for case, (seed, hidden, bias) in enumerate(CASES):
            rows = scene_rows(source, case, frames)
            available = [row for row in rows if row["mean_error"]]
            rmse = [
                math.sqrt(math.fsum(float(row[f"{method}_error"])**2 for row in available) / len(available))
                if available else "" for method in ("mean", "median")
            ]
            writer.writerow((case, seed, hidden, bias, len(available), *rmse))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, choices=(96, 384), default=96)
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("case")
    one.add_argument("case", type=int)
    one.add_argument("output", type=Path)
    all_cases = commands.add_parser("aggregate")
    all_cases.add_argument("source", type=Path)
    all_cases.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "case":
        if not 0 <= args.case < len(CASES):
            parser.error("invalid case index")
        write_case(args.case, args.frames, args.output)
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        summarize(args.source, args.frames, args.output / "scenario-summary.csv")
        render(scene_rows(args.source, CASES.index((0, 4, 10.0)), args.frames), args.output)
