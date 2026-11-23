#!/usr/bin/env python3
"""Render the committed OceanBench metric tables as a forecast-lead GIF."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def lead_values(table):
    columns = table["columns"]
    indices = [i for i, name in enumerate(columns) if name.startswith("Lead day ")]
    leads = [int(columns[i].removeprefix("Lead day ")) for i in indices]
    values = np.asarray(table["values"], dtype=float)[:, indices]
    return np.asarray(leads), values


def render(results_path, output_path, provenance_path):
    results = json.loads(results_path.read_text(encoding="utf-8"))
    tables = list(results["tables"].items())
    frames = []

    # Bounds are computed once from every lead, then reused for every frame.
    bounds = {}
    for branch, table in tables:
        _, values = lead_values(table)
        shown = values[: min(5, len(values))]
        finite = shown[np.isfinite(shown)]
        low, high = float(finite.min()), float(finite.max())
        padding = max((high - low) * 0.08, abs(high) * 0.02, 1e-9)
        bounds[branch] = [low - padding, high + padding]

    for current_lead in range(1, 11):
        fig, axes = plt.subplots(3, 3, figsize=(12, 8.8), constrained_layout=True)
        for ax, (branch, table) in zip(axes.flat, tables):
            leads, values = lead_values(table)
            for row in values[: min(5, len(values))]:
                available = (leads <= current_lead) & np.isfinite(row)
                ax.plot(leads[available], row[available], marker="o", markersize=3, linewidth=1.4)
            ax.axvline(current_lead, color="#d62728", linewidth=1, linestyle="--")
            ax.set_xlim(1, 10)
            ax.set_ylim(*bounds[branch])
            ax.set_title(branch, fontsize=9)
            ax.set_xlabel("Forecast lead day", fontsize=8)
            ax.set_ylabel("Published metric", fontsize=8)
            ax.grid(alpha=0.2)
            ax.tick_params(labelsize=7)
        fig.suptitle(
            f"OceanBench GLONET audited metrics through forecast lead day {current_lead}",
            fontsize=14,
        )
        fig.canvas.draw()
        rgba = np.asarray(fig.canvas.buffer_rgba())
        frames.append(Image.fromarray(rgba[:, :, :3].copy()).convert("P", palette=Image.Palette.ADAPTIVE))
        plt.close(fig)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=650,
        loop=0,
        optimize=False,
        disposal=2,
    )
    with Image.open(output_path) as image:
        metadata = {
            "source": str(results_path),
            "source_sha256": sha256(results_path),
            "artifact": str(output_path),
            "artifact_sha256": sha256(output_path),
            "format": image.format,
            "dimensions": list(image.size),
            "frames": image.n_frames,
            "lead_days": list(range(1, 11)),
            "frame_duration_ms": 650,
            "stable_axes": bounds,
            "encoding": "Each panel reveals up to five published metric rows; the red dashed line marks the current forecast lead.",
        }
    provenance_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    render(args.results, args.output, args.provenance)


if __name__ == "__main__":
    main()
