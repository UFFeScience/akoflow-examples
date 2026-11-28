"""Render fixed-scale fusion panels and classification errors over a PAN sweep."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from fusion import CASES, FACTORS, LEVELS, SIZE, calibrate, classify, condition, evaluate, images, scene

LABELS = ("Truth", "Resampled", "PAN detail", "PCA")
STEP = 2 * SIZE
BAND_LIMITS = (.15, .70)
OUTCOMES = np.array(((20, 22, 25), (62, 147, 103), (239, 153, 72), (151, 91, 169)), dtype=np.uint8)


def rgb(bands):
    low, high = BAND_LIMITS
    scaled = np.clip((bands[..., ::-1] - low) / (high - low), 0, 1)
    return Image.fromarray((255 * scaled).astype(np.uint8)).resize((STEP, STEP), Image.Resampling.NEAREST)


def classifications(target, prediction):
    labels = prediction.astype(int) + 2 * target.astype(int)
    labels[target & prediction] = 1
    labels[prediction & ~target] = 2
    labels[~prediction & target] = 3
    return Image.fromarray(OUTCOMES[labels]).resize((STEP, STEP), Image.Resampling.NEAREST)


def panel(seed, factor, level, models):
    target, bands, pan = scene(seed, level)
    treatments, _ = images(bands, pan, factor)
    case = CASES.index((seed, factor, level))
    metrics = evaluate(case, models)
    canvas = Image.new("RGB", (4 * STEP, 2 * STEP + 70), "#141619")
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 6), f"Case {case} | {factor}x reduction | PAN interference {level:g}", fill="white")
    canvas.paste(rgb(bands), (0, 48))
    canvas.paste(classifications(target, target), (0, 48 + STEP))
    for i, title in enumerate(LABELS):
        draw.text((i * STEP + 6, 27), title, fill="white")
    for i, (bands_fused, values, centers) in enumerate(
        zip(treatments, metrics, models[condition(factor, level)]), 1
    ):
        x = i * STEP
        _, pred = classify(bands_fused, np.asarray(centers))
        canvas.paste(rgb(bands_fused), (x, 48))
        canvas.paste(classifications(target, pred), (x, 48 + STEP))
        draw.text((x + 5, 2 * STEP + 54),
                  f"IoU {values['centroid_iou']:.3f} | edge RMSE {values['edge_rmse']:.3f}", fill="white")
    return canvas


def render(output, models, seed, factor):
    panels = [panel(seed, factor, level, models) for level in LEVELS]
    panels[0].save(output / "pansharpening-classification.png")
    panels[0].save(output / "pan-interference-sweep.gif", save_all=True,
                   append_images=panels[1:], duration=1300, loop=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--models", type=Path)
    parser.add_argument("--seed", type=int, choices=range(64), default=0, metavar="SEED")
    parser.add_argument("--factor", type=int, choices=FACTORS, default=2)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    models = json.loads(args.models.read_text()) if args.models else calibrate()
    render(args.output, models, args.seed, args.factor)
    if args.models is None:
        rows = [row for case in range(len(CASES)) for row in evaluate(case, models)]
        with (args.output / "pilot-metrics.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
