"""Render synthetic IDW maps and a comparison animation."""

import argparse
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from PIL import Image

from study import HEIGHT, WIDTH, center, truth


def render(output):
    grids = json.loads((output / "grids.json").read_bytes())
    frames = []
    for scenario in range(8):
        actual = [[truth(scenario, *center(i, j)) for i in range(WIDTH)] for j in range(HEIGHT)]
        raw, filtered = (grids[f"s{scenario}-{condition}-p4"] for condition in ("raw", "filtered"))
        raw_error, filtered_error = (
            [[value - target for value, target in zip(row, ref)] for row, ref in zip(estimate, actual)]
            for estimate in (raw, filtered)
        )
        fig, axes = plt.subplots(2, 3, figsize=(9, 5), layout="constrained")
        fields = (actual, raw, filtered, None, raw_error, filtered_error)
        titles = ("Analytic reference", "Raw estimates", "Filtered estimates",
                  "", "Raw error", "Filtered error")
        for index, (axis, values, title) in enumerate(zip(axes.flat, fields, titles)):
            if values is None:
                axis.axis("off")
                continue
            limit = 2 if index < 3 else 4
            axis.imshow(values, origin="lower", extent=(0, 1, 0, 1), aspect="auto",
                        cmap="viridis" if index < 3 else "coolwarm", vmin=-limit, vmax=limit)
            axis.axvspan(0.43, 0.57, facecolor="none", edgecolor="black", linestyle=":", linewidth=0.8)
            axis.set_title(title)
            axis.set(xlabel="x", ylabel="y")
        fig.suptitle(f"Synthetic surface {scenario} · IDW exponent 4")
        if scenario == 3:
            fig.savefig(output / "idw-comparison.png", dpi=120)
        with io.BytesIO() as image:
            fig.savefig(image, format="png", dpi=90)
            image.seek(0)
            with Image.open(image) as frame:
                frames.append(frame.convert("RGB"))
        plt.close(fig)
    frames[0].save(output / "idw-surfaces.gif", save_all=True, append_images=frames[1:],
                   duration=950, loop=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    render(parser.parse_args().output)
