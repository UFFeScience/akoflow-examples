"""Render the two validated PRODES series and export their measurements."""

import argparse
import csv
import io
import json
from pathlib import Path

import matplotlib
from PIL import Image

matplotlib.use("Agg")
from matplotlib import pyplot as plt

SERIES = (
    ("amazon", "Legal Amazon", "Consolidated annual rate", "#16745a"),
    ("cerrado", "Cerrado", "Mapped annual increment", "#ac5f32"),
)


def render(inputs: Path, output: Path) -> None:
    series = {}
    for key, *_ in SERIES:
        result = json.loads((inputs / f"{key}.json").read_text())
        if result["region"] != key or [row["year"] for row in result["series"]] != list(range(2020, 2026)):
            raise ValueError(f"Invalid reduction result for {key}")
        series[key] = result["series"]

    output.mkdir(parents=True, exist_ok=True)
    with (output / "prodes-annual.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["region", "year", "area_km2", "location_count"])
        writer.writeheader()
        for key, rows in series.items():
            writer.writerows({"region": key, **row} for row in rows)

    frames = []
    for year in range(2020, 2026):
        figure, axes = plt.subplots(1, 2, figsize=(10, 4.6), layout="constrained")
        figure.suptitle(f"INPE PRODES annual deforestation series, through {year}")
        for axis, (key, title, measure, color) in zip(axes, SERIES):
            rows = series[key]
            visible = [row for row in rows if row["year"] <= year]
            axis.plot([row["year"] for row in visible], [float(row["area_km2"]) for row in visible],
                      color=color, marker="o", linewidth=2)
            axis.set(title=f"{title}\n{measure}", xlabel="PRODES end-year", ylabel="Area (km²)",
                     xlim=(2019.8, 2025.2), ylim=(0, 14000), xticks=range(2020, 2026))
            axis.grid(axis="y", alpha=0.25)
        figure.supxlabel("Source: INPE BiomasBR / TerraBrasilis · CC BY-SA 4.0", fontsize=9)
        if year == 2025:
            figure.savefig(output / "prodes-annual.png", dpi=115)
        with io.BytesIO() as buffer:
            figure.savefig(buffer, format="png", dpi=100)
            buffer.seek(0)
            with Image.open(buffer) as frame:
                frames.append(frame.convert("RGB"))
        plt.close(figure)
    frames[0].save(output / "prodes-annual.gif", save_all=True, append_images=frames[1:],
                   duration=850, loop=0, disposal=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(args.inputs, args.output)
