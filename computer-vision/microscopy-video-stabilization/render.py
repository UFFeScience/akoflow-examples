"""Render a measured sequence and alignment residuals with fixed scales."""

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from stabilize import CASES, FRAMES, SIZE, bilinear, generate

METHODS = ("unregistered", "phase-anchored", "phase-chained")
LABELS = ("Observed", "Phase / anchored", "Phase / chained")
ZOOM = 2
SIDE = SIZE * ZOOM
HEADER = 22


def image_of(array, low, high):
    pixels = np.nan_to_num(np.clip((array - low) / (high - low), 0, 1))
    return Image.fromarray((255 * pixels).astype(np.uint8)).resize((SIDE, SIDE), Image.Resampling.NEAREST)


def render(case, source, output):
    with source.open(newline="") as stream:
        rows = {(int(row["frame"]), row["method"]): row for row in csv.DictReader(stream)}
    frames, truth = generate(*CASES[case])
    output.mkdir(parents=True, exist_ok=True)
    yy, xx = np.indices((SIZE, SIZE))
    images = []
    for i, frame in enumerate(frames):
        canvas = Image.new("RGB", (3 * SIDE, 2 * (SIDE + HEADER) + HEADER), "#141418")
        draw = ImageDraw.Draw(canvas)
        draw.text((5, 4), f"Frame {i + 1}/{FRAMES}   True scene motion (y, x): {truth[i,0]:+.2f}, {truth[i,1]:+.2f} px", fill="white")
        for column, (method, label) in enumerate(zip(METHODS, LABELS)):
            row = rows[i, method]
            if not np.allclose([float(row["truth_y"]), float(row["truth_x"])], truth[i]):
                raise ValueError(f"CSV does not describe case {case}")
            x0 = SIDE * column
            draw.text((x0 + 5, HEADER + 4), f"{label} | {row['status']}", fill="white")
            if row["status"] != "ok":
                continue
            y = yy - float(row["alignment_y"])
            x = xx - float(row["alignment_x"])
            valid = (y >= 0) & (x >= 0) & (y <= SIZE - 1) & (x <= SIZE - 1)
            aligned = np.full(frame.shape, np.nan)
            aligned[valid] = bilinear(frame, y[valid], x[valid])
            canvas.paste(image_of(aligned, -3, 3), (x0, 2 * HEADER))
            mae = float(row["common_mae"])
            error = float(row["trajectory_error_px"])
            draw.text((x0 + 5, SIDE + 2 * HEADER + 4),
                      f"MAE {mae:.3f} | drift {error:.2f} px", fill="white")
            residual = np.abs(aligned - frames[0])
            canvas.paste(image_of(residual, 0, 3), (x0, SIDE + 3 * HEADER))
        images.append(canvas)
    images[-1].save(output / "stabilization-residuals.png")
    images = [image.resize((image.width // ZOOM, image.height // ZOOM), Image.Resampling.BOX)
              .quantize(colors=32) for image in images]
    images[0].save(output / "stabilization.gif", save_all=True,
                   append_images=images[1:], duration=140, loop=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=int, choices=range(len(CASES)), metavar="CASE")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(args.case, args.source, args.output)
