"""Run one independent Green–Ampt batch and write compact scientific results."""

import argparse
import json
from math import isfinite
from pathlib import Path
from time import perf_counter

from infiltration import bracketed_depth, ponding_time, sample_column
from scenarios import batches, columns

COLUMN_COUNT = 256
REFERENCE_COLUMNS = 4
REFERENCE_TOLERANCE_MM = 1e-6


def run_batch(batch):
    conditions = list(columns(batch, COLUMN_COUNT))
    results = []
    error = 0.0
    phase_time = {"rainfall_only": 0.0, "post_ponding": 0.0, "verification": 0.0}
    for index, (rain, conductivity, suction_deficit) in enumerate(conditions):
        onset = ponding_time(rain, conductivity, suction_deficit)
        samples = list(sample_column(rain, conductivity, suction_deficit, phase_time))
        if index < REFERENCE_COLUMNS:
            start = perf_counter()
            for time, depth, _ in samples:
                error = max(error, abs(depth - bracketed_depth(rain, conductivity, suction_deficit, time)))
            phase_time["verification"] += perf_counter() - start
        _, depth, runoff = samples[-1]
        results.append({
            "column": index, "conductivity_mm_h": conductivity, "suction_deficit_mm": suction_deficit,
            "ponding_hours": onset if isfinite(onset) else None,
            "infiltration_mm": depth, "runoff_mm": runoff,
        })
    if error > REFERENCE_TOLERANCE_MM:
        raise ArithmeticError(f"{batch['id']}: reference error {error:.6g} mm")
    return {"batch": batch, "columns": results, "max_reference_error_mm": error}, phase_time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=int, choices=range(512), metavar="0..511")
    parser.add_argument("output", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    batch = list(batches())[args.batch]
    if args.manifest is not None and json.loads(args.manifest.read_text())[args.batch] != batch:
        raise ValueError(f"Manifest does not match batch {batch['id']}")
    result, timing = run_batch(batch)
    args.output.mkdir(parents=True, exist_ok=True)
    for suffix, payload in (("results", result), ("timing", timing)):
        (args.output / f"{batch['id']}-{suffix}.json").write_text(
            json.dumps(payload, allow_nan=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
