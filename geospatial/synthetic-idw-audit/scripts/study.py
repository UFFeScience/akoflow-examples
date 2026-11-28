"""Deterministic blocked interpolation experiment inspired by Kida and Santos."""

import argparse
import csv
import hashlib
import json
from math import cos, fsum, hypot, isclose, pi, sin, sqrt
from pathlib import Path
from random import Random
from statistics import median

WIDTH, HEIGHT = 64, 32
BLOCK_SIZE = 8
BLOCKS = WIDTH * HEIGHT // BLOCK_SIZE**2
EXPONENTS = (2, 4)
CONDITIONS = ("raw", "filtered")


def truth(scenario, x, y):
    return sin(pi * (1 + scenario % 4) * x + scenario / 8) + 0.6 * cos(
        pi * (1 + scenario // 4) * y) + 0.2 * x * y


def idw(sites, x, y, exponent):
    distances = [(hypot(x - a, y - b), value) for a, b, value in sites]
    minimum = min(distance for distance, _ in distances)
    if minimum == 0:
        return next(value for distance, value in distances if distance == 0)
    weights = [(minimum / distance)**exponent for distance, _ in distances]
    return fsum(w * pair[1] for w, pair in zip(weights, distances)) / fsum(weights)


def reference_idw(sites, x, y, exponent):
    squared_distances = [((x - a)**2 + (y - b)**2, value) for a, b, value in sites]
    for distance, value in squared_distances:
        if distance == 0:
            return value
    inverse_power = -exponent / 2
    return fsum(value * distance**inverse_power for distance, value in squared_distances) / fsum(
        distance**inverse_power for distance, _ in squared_distances
    )


def canonicalize(points):
    sites = {}
    for point in sorted(points, key=lambda point: point["id"]):
        sites.setdefault((point["x"], point["y"]), []).append(point)
    return [
        {"x": x, "y": y, "value": fsum(point["value"] for point in group) / len(group),
         "ids": [point["id"] for point in group]}
        for (x, y), group in sites.items()
    ]


def coordinates(sites):
    return [(site["x"], site["y"], site["value"]) for site in sites]


def held_out(x):
    return 0.43 <= x < 0.57


def scenario_input(scenario):
    seed = 395000 + scenario
    rng = Random(seed)
    points = []
    while len(points) < 96:
        index = len(points)
        if index < 48:
            x, y = rng.random(), rng.random()
        else:
            center = (0.25, 0.75)[index % 2]
            x, y = rng.gauss(center, 0.045), rng.gauss(center, 0.045)
        if 0 <= x <= 1 and 0 <= y <= 1 and not held_out(x):
            points.append({"id": index, "x": x, "y": y, "value": truth(scenario, x, y)})
    injected = sorted(rng.sample(range(96), 5)) if scenario % 2 else []
    for index in injected:
        points[index]["value"] += 8 if index % 2 else -8
    return {"id": scenario, "seed": seed, "points": points, "injected_ids": injected}


def fit(points):
    raw = canonicalize(points)
    sites = coordinates(raw)
    residuals = [
        value - idw(sites[:index] + sites[index + 1:], x, y, 2)
        for index, (x, y, value) in enumerate(sites)
    ]
    center = median(residuals)
    mad = median(abs(value - center) for value in residuals)
    threshold = 6 * max(1.4826 * mad, 0.025)
    filtered, removed = [], []
    for site, residual in zip(raw, residuals):
        if abs(residual - center) > threshold:
            removed.extend(site["ids"])
        else:
            filtered.append(site)
    if not filtered:
        raise ValueError("Treatment removed all training sites")
    return {"raw": raw, "filtered": filtered, "removed_ids": sorted(removed)}


def cases():
    for scenario in range(8):
        for condition in CONDITIONS:
            for exponent in EXPONENTS:
                yield scenario, condition, exponent


def block_name(scenario, condition, exponent, block):
    return f"s{scenario}-{condition}-p{exponent}-block-{block:02d}"


def cells(block):
    block_x, block_y = divmod(block, HEIGHT // BLOCK_SIZE)
    for i in range(block_x * BLOCK_SIZE, (block_x + 1) * BLOCK_SIZE):
        for j in range(block_y * BLOCK_SIZE, (block_y + 1) * BLOCK_SIZE):
            yield i, j


def center(i, j):
    return (i + 0.5) / WIDTH, (j + 0.5) / HEIGHT


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n")


def prepare(manifest, output):
    payload = manifest.read_bytes()
    expected = manifest.with_suffix(".sha256").read_text().split()[0]
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("Frozen sample manifest checksum mismatch")
    scenarios = json.loads(payload)
    for scenario in scenarios:
        result = fit(scenario["points"])
        result["injected_ids"] = scenario["injected_ids"]
        write_json(output / f"sites-{scenario['id']}.json", result)


def predict(scenario, condition, exponent, block, source, output):
    sites = coordinates(json.loads(source.read_bytes())[condition])
    values = [[i, j, idw(sites, *center(i, j), exponent)] for i, j in cells(block)]
    write_json(output / (block_name(scenario, condition, exponent, block) + ".json"), values)


def assemble(source, output):
    output.mkdir(parents=True, exist_ok=True)
    table, grids = [], {}
    for scenario, condition, exponent in cases():
        data = json.loads((source / f"sites-{scenario}.json").read_bytes())
        sites = coordinates(data[condition])
        expected_cells = {(i, j) for i in range(WIDTH) for j in range(HEIGHT)}
        estimates = {}
        for block in range(BLOCKS):
            rows = json.loads((source / (block_name(scenario, condition, exponent, block) + ".json")).read_bytes())
            if [(i, j) for i, j, _ in rows] != list(cells(block)):
                raise ValueError(f"Block {block} does not match its declared coordinates")
            for i, j, value in rows:
                if (i, j) in estimates or not isclose(value, reference_idw(sites, *center(i, j), exponent),
                                                       abs_tol=1e-12, rel_tol=0):
                    raise ValueError(f"Duplicate or invalid estimate at {(i, j)}")
                estimates[i, j] = value
        if estimates.keys() != expected_cells:
            raise ValueError("Raster coverage mismatch")
        residuals = [
            value - truth(scenario, *center(i, j))
            for (i, j), value in estimates.items() if held_out(center(i, j)[0])
        ]
        injected = set(data["injected_ids"])
        removed = set(data["removed_ids"]) if condition == "filtered" else set()
        table.append({"scenario": scenario, "condition": condition, "exponent": exponent,
                      "holdout_cells": len(residuals), "mae": fsum(map(abs, residuals)) / len(residuals),
                      "rmse": sqrt(fsum(error**2 for error in residuals) / len(residuals)),
                      "true_positives": len(injected & removed), "false_positives": len(removed - injected)})
        grids[f"s{scenario}-{condition}-p{exponent}"] = [
            [estimates[i, j] for i in range(WIDTH)] for j in range(HEIGHT)
        ]
    write_json(output / "grids.json", grids)
    with (output / "metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=table[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(table)
    write_json(output / "validation.json", {
        "passed": True, "blocks": len(table) * BLOCKS, "grids": len(table),
        "sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                   for name in ("grids.json", "metrics.csv")},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("freeze").add_argument("output", type=Path)
    preparation = commands.add_parser("prepare")
    preparation.add_argument("manifest", type=Path)
    preparation.add_argument("output", type=Path)
    prediction = commands.add_parser("predict")
    prediction.add_argument("scenario", type=int, choices=range(8))
    prediction.add_argument("condition", choices=CONDITIONS)
    prediction.add_argument("exponent", type=int, choices=EXPONENTS)
    prediction.add_argument("block", type=int, choices=range(BLOCKS))
    prediction.add_argument("source", type=Path)
    prediction.add_argument("output", type=Path)
    assembly = commands.add_parser("assemble")
    assembly.add_argument("source", type=Path)
    assembly.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        write_json(args.output, [scenario_input(index) for index in range(8)])
    elif args.action == "prepare":
        prepare(args.manifest, args.output)
    elif args.action == "predict":
        predict(args.scenario, args.condition, args.exponent, args.block, args.source, args.output)
    else:
        assemble(args.source, args.output)


if __name__ == "__main__":
    main()
