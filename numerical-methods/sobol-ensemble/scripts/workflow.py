"""Fixed-manifest randomized Sobol and pseudorandom integration."""

import argparse
import json
import math
import resource
import time
from pathlib import Path

import numpy as np
from scipy.stats import qmc

DIMENSION = 16
EXPONENTS = tuple(range(10, 21))
REFERENCES = {"smooth": 1.5**DIMENSION, "indicator": 0.5}
TASKS = 128
REPLICATES = 32


def manifest():
    seeds = np.random.SeedSequence(107).generate_state(TASKS)
    if len(set(seeds)) != TASKS:
        raise ValueError("The seed manifest contains repeated seeds")
    return [
        {"index": index, "seed": int(seed), "replicate": index % REPLICATES,
         "method": ("sobol", "pseudo")[index // 64],
         "integrand": ("smooth", "indicator")[(index // REPLICATES) % 2]}
        for index, seed in enumerate(seeds)
    ]


def smooth(points):
    return np.prod(1 + points, axis=1)


def indicator(points):
    return np.sum(points, axis=1) > DIMENSION / 2


def estimates(task, exponents=EXPONENTS, function=None):
    rng = np.random.default_rng(task["seed"])
    sobol = None
    if task["method"] == "sobol":
        sobol = qmc.Sobol(DIMENSION, scramble=True, bits=30, rng=rng)

    function = function or {"smooth": smooth, "indicator": indicator}[task["integrand"]]
    total = 0.0
    previous = 0
    rows = []
    for exponent in exponents:
        count = 1 << exponent
        additional = count - previous
        if sobol is None:
            points = rng.random((additional, DIMENSION))
        else:
            points = sobol.random_base2(additional.bit_length() - 1)
        values = function(points)
        if values.shape != (additional,) or not np.isfinite(values).all():
            raise ValueError("Invalid integration output")
        total += float(np.sum(values, dtype=np.float64))
        rows.append({"exponent": exponent, "count": count, "estimate": total / count})
        previous = count
    return rows


def prepare():
    tasks = manifest()
    for index in (0, 64):
        constant = estimates(tasks[index], (5, 6), lambda points: np.ones(len(points)))
        if [row["estimate"] for row in constant] != [1, 1]:
            raise ValueError("Constant-function fixture failed")
        linear = estimates(tasks[index], (5, 6), lambda points: points[:, 0])
        direct_rng = np.random.default_rng(tasks[index]["seed"])
        if index == 0:
            direct = qmc.Sobol(DIMENSION, scramble=True, bits=30, rng=direct_rng).random_base2(6)
        else:
            direct = direct_rng.random((64, DIMENSION))
        if not all(math.isclose(row["estimate"], direct[:row["count"], 0].mean(), abs_tol=1e-15)
                   for row in linear):
            raise ValueError("Nested prefix disagrees with direct generation")
    boundary = np.full((3, DIMENSION), 0.5)
    boundary[0, 0] = 0.25
    boundary[2, 0] = 0.75
    if indicator(boundary).tolist() != [False, False, True]:
        raise ValueError("Indicator boundary fixture failed")
    Path("manifest.json").write_text(json.dumps(tasks, sort_keys=True) + "\n")


def replicate(index):
    task = manifest()[index]
    start = time.monotonic()
    rows = estimates(task)
    result = {"task": task, "reference": REFERENCES[task["integrand"]], "prefixes": rows}
    Path(f"replicate-{index:03d}.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    measures = {"index": index, "seconds": time.monotonic() - start,
                "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    Path(f"timing-{index:03d}.json").write_text(json.dumps(measures, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="mode", required=True)
    subcommands.add_parser("prepare")
    worker = subcommands.add_parser("replicate")
    worker.add_argument("index", type=int, choices=range(TASKS), metavar="INDEX")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    else:
        replicate(args.index)
