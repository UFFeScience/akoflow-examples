"""Validate the frozen infiltration campaign and write one deterministic row per batch."""

import argparse
import csv
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from statistics import fmean

from infiltration import MASS_TOLERANCE_MM, STORM_HOURS
from run_batch import COLUMN_COUNT, REFERENCE_TOLERANCE_MM
from scenarios import batches


def summarize_batch(data, batch):
    if data["batch"] != batch:
        raise ValueError(f"{batch['id']}: manifest mismatch")
    records = data["columns"]
    if [row["column"] for row in records] != list(range(COLUMN_COUNT)):
        raise ValueError(f"{batch['id']}: missing or repeated column")
    rainfall = batch["rain_mm_h"] * STORM_HOURS
    error = data["max_reference_error_mm"]
    if not 0 <= error <= REFERENCE_TOLERANCE_MM:
        raise ValueError(f"{batch['id']}: reference error outside tolerance")
    ponding_count = 0
    for row in records:
        infiltration, runoff = row["infiltration_mm"], row["runoff_mm"]
        if not (0 <= infiltration and 0 <= runoff and
                abs(infiltration + runoff - rainfall) <= MASS_TOLERANCE_MM):
            raise ValueError(f"{batch['id']}: invalid storm mass balance")
        onset = row["ponding_hours"]
        if onset is not None and not (isfinite(onset) and onset >= 0):
            raise ValueError(f"{batch['id']}: invalid ponding time")
        ponding_count += onset is not None and onset < STORM_HOURS
    return {
        **batch,
        "columns": COLUMN_COUNT,
        "ponded_columns": ponding_count,
        "ponded_fraction": ponding_count / COLUMN_COUNT,
        "mean_infiltration_mm": fmean(row["infiltration_mm"] for row in records),
        "mean_runoff_mm": fmean(row["runoff_mm"] for row in records),
        "max_reference_error_mm": error,
    }


def summarize_timing(batch_id, timing):
    phases = ("rainfall_only", "post_ponding", "verification")
    if set(timing) != set(phases) or any(not (isfinite(value) and value >= 0) for value in timing.values()):
        raise ValueError(f"{batch_id}: invalid phase timing")
    return {"id": batch_id, **{f"{phase}_seconds": timing[phase] for phase in phases}}


def write_table(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = list(batches())
    files = {path.name: path for path in args.input.glob("batch-*-results.json")}
    expected = {f"{batch['id']}-results.json" for batch in manifest}
    if files.keys() != expected:
        raise ValueError(f"Expected 512 batches; missing {len(expected - files.keys())}, extra {len(files.keys() - expected)}")
    rows = [summarize_batch(json.loads(files[f"{batch['id']}-results.json"].read_text()), batch)
            for batch in manifest]
    timing_rows = [
        summarize_timing(batch["id"], json.loads((args.input / f"{batch['id']}-timing.json").read_text()))
        for batch in manifest
    ]
    args.output.mkdir(parents=True, exist_ok=True)
    table = args.output / "infiltration-batches.csv"
    write_table(table, rows)
    write_table(args.output / "infiltration-timing.csv", timing_rows)
    validation = {
        "passed": True, "batches": len(rows), "columns": sum(row["columns"] for row in rows),
        "ponded_columns": sum(row["ponded_columns"] for row in rows),
        "max_reference_error_mm": max(row["max_reference_error_mm"] for row in rows),
    }
    from render import render

    validation["animation_frames"] = render(rows, args.output)
    validation["sha256"] = {
        name: sha256((args.output / name).read_bytes()).hexdigest()
        for name in (table.name, "rainfall-runoff.png", "rainfall-runoff.gif")
    }
    (args.output / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")


if __name__ == "__main__":
    main()
