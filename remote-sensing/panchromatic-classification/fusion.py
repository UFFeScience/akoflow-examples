"""Evaluate whether pansharpening improves a synthetic crop classification."""

import argparse
import csv
import json
from itertools import product
from pathlib import Path

import numpy as np

SIZE = 96
FACTORS = (2, 3, 4, 6)
LEVELS = (0.0, 0.5, 1.0)
CALIBRATION = range(5540, 5548)
CASES = tuple(product(range(64), FACTORS, LEVELS))
METHODS = ("resampled", "detail", "pca")
TOLERANCE = 1e-12


def block_mean(image, factor):
    rows, cols = image.shape[:2]
    return image.reshape(rows // factor, factor, cols // factor, factor,
                         *image.shape[2:]).mean(axis=(1, 3))


def expand(image, factor):
    return image.repeat(factor, axis=0).repeat(factor, axis=1)


def scene(seed, level):
    y, x = np.indices((SIZE, SIZE))
    rng = np.random.default_rng(seed)
    edge = 47 + rng.integers(-8, 9) + 7 * np.sin(y / 13 + rng.uniform(0, 6))
    target = (x > edge) ^ (((y-53)**2 + (x-26)**2) < rng.integers(7, 12)**2)
    texture = .055 * np.sin(y / 5) + .03 * np.cos(x / 7)
    bands = np.array([.41, .34, .35]) + target[..., None] * np.array([-.12, .18, .04])
    bands += texture[..., None] + rng.normal(0, .01, bands.shape)
    pan = bands @ np.array([.25, .50, .25])
    pan += level * (.28 * np.sin((x+y) / 4 + rng.uniform(0, 6)) + .14 * (y > 48))
    return target, bands, pan


def pca_sharpen(coarse, pan, factor):
    base = expand(coarse, factor)
    centered = coarse - coarse.mean(axis=(0, 1))
    flat = centered.reshape(-1, coarse.shape[-1])
    variance, directions = np.linalg.eigh(flat.T @ flat / len(flat))
    if (pan.std() <= TOLERANCE or variance[-1] <= TOLERANCE
            or variance[-1] - variance[-2] <= TOLERANCE):
        return base, "degenerate"
    first = directions[:, -1]
    component = centered @ first
    low_pan = block_mean(pan, factor)
    agreement = np.mean(component * (low_pan - low_pan.mean()))
    sign = first[np.argmax(np.abs(first))] if abs(agreement) <= TOLERANCE else agreement
    if sign < 0:
        first = -first
        component = -component
    matched = (pan - pan.mean()) * (component.std() / pan.std())
    return base + (matched - expand(component, factor))[..., None] * first, "ok"


def images(bands, pan, factor):
    coarse = block_mean(bands, factor)
    base = expand(coarse, factor)
    residual = pan - expand(block_mean(pan, factor), factor)
    detail = base + residual[..., None] * np.array([1.4, .15, .25])
    pca, status = pca_sharpen(coarse, pan, factor)
    return (base, detail, pca), status


def calibrate():
    models = {}
    for factor, level in product(FACTORS, LEVELS):
        totals = np.zeros((len(METHODS), 2, 3))
        counts = np.zeros(2, dtype=int)
        for seed in CALIBRATION:
            target, bands, pan = scene(seed, level)
            fused, _ = images(bands, pan, factor)
            for cls, mask in enumerate((~target, target)):
                counts[cls] += mask.sum()
                for method, image in enumerate(fused):
                    totals[method, cls] += image[mask].sum(axis=0)
        models[condition(factor, level)] = (totals / counts[None, :, None]).tolist()
    return models


def condition(factor, level):
    return f"{factor}-{LEVELS.index(level)}"


def classify(image, centers):
    fixed = image[..., 1] - image[..., 0] > .10
    distance = ((image[..., None, :] - centers[None, None, ...]) ** 2).sum(axis=-1)
    return fixed, distance.argmin(axis=-1) == 1


def evaluate(case, models):
    seed, factor, level = CASES[case]
    target, bands, pan = scene(seed, level)
    fused, status = images(bands, pan, factor)
    rows = []
    for method, image, centers in zip(METHODS, fused, models[condition(factor, level)]):
        fixed, trained = classify(image, np.asarray(centers))
        edge_rmse = np.sqrt(sum(np.mean(np.diff(image-bands, axis=axis)**2) for axis in (0, 1)))
        spectral_rmse = np.sqrt(np.mean((image-bands)**2, axis=(0, 1)))
        rows.append({
            "id": case, "seed": seed, "factor": factor, "interference": level,
            "method": method, "status": status if method == "pca" else "ok",
            "edge_rmse": edge_rmse,
            **{f"band_{band}_rmse": value for band, value in zip((4, 5, 6), spectral_rmse)},
            "fixed_iou": np.count_nonzero(fixed & target) / np.count_nonzero(fixed | target),
            "centroid_iou": np.count_nonzero(trained & target) / np.count_nonzero(trained | target),
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    calibration = commands.add_parser("calibrate")
    calibration.add_argument("output", type=Path)
    case = commands.add_parser("case")
    case.add_argument("id", type=int, metavar="CASE", choices=range(len(CASES)))
    case.add_argument("models", type=Path)
    case.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "calibrate":
        args.output.write_text(json.dumps(calibrate(), indent=2) + "\n")
        return
    rows = evaluate(args.id, json.loads(args.models.read_text()))
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
