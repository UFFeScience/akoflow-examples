"""Render maps of frozen DETER alerts with a common scale across months."""

from collections import Counter
import gzip
from io import BytesIO
import json
from math import cos, radians

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LogNorm
from PIL import Image

from audit_month import CELL_DEGREES


def boundaries(snapshot):
    path = snapshot / "ibge-amazon-states.geojson.gz"
    with gzip.open(path, "rt") as stream:
        features = json.load(stream)["features"]
    lines = []
    for item in features:
        geometry = item["geometry"]
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        lines.extend(polygon[0] for polygon in polygons if polygon)
    return lines


def monthly_grids(audits):
    grids = []
    for audit in audits:
        grid = Counter({(lon, lat): count for lon, lat, count in audit["grid"]})
        grids.append(grid)
    return grids


def map_axes(lines):
    figure, axis = plt.subplots(figsize=(8.4, 5.4), layout="constrained")
    axis.add_collection(LineCollection(lines, colors="#516050", linewidths=0.45, zorder=2))
    axis.set(xlim=(-74, -43), ylim=(-19, 6), xlabel="Longitude (degrees)", ylabel="Latitude (degrees)",
             aspect=1 / cos(radians(7)))
    axis.grid(alpha=0.15)
    figure.text(0.02, 0.015, "Alerts: INPE DETER / TerraBrasilis · State outlines: IBGE 2024",
                fontsize=8, color="#444444")
    return figure, axis


def centers(grid):
    return [[(lon + 0.5) * CELL_DEGREES, (lat + 0.5) * CELL_DEGREES]
            for lon, lat in grid]


def render(audits, snapshot, output):
    lines = boundaries(snapshot)
    grids = monthly_grids(audits)
    combined = sum(grids, Counter())
    overall = LogNorm(vmin=1, vmax=max(2, max(combined.values())))
    figure, axis = map_axes(lines)
    coordinates = centers(combined)
    dots = axis.scatter(*zip(*coordinates), c=list(combined.values()), marker="s", s=6,
                        linewidths=0, norm=overall, cmap="magma", zorder=3)
    axis.set_title(f"DETER alert records · {audits[0]['month']} to {audits[-1]['month']}")
    figure.colorbar(dots, ax=axis, label="Alert records per 0.25° cell")
    plot_path = output / "deter-reference-map.png"
    figure.savefig(plot_path, dpi=140)
    plt.close(figure)

    monthly = LogNorm(vmin=1, vmax=max(2, max(max(grid.values(), default=0) for grid in grids)))
    figure, axis = map_axes(lines)
    first_positions = centers(grids[0]) or [[-180, -90]]
    dots = axis.scatter(*zip(*first_positions), c=list(grids[0].values()) or [1],
                        marker="s", s=6, linewidths=0, norm=monthly, cmap="magma", zorder=3)
    figure.colorbar(dots, ax=axis, label="Monthly alert records per 0.25° cell")
    frames = []
    for audit, grid in zip(audits, grids):
        dots.set_offsets(centers(grid) or [[-180, -90]])
        dots.set_array(list(grid.values()) or [1])
        axis.set_title(f"DETER alerts · {audit['month']} · {audit['features']:,} source records")
        stream = BytesIO()
        figure.savefig(stream, format="png", dpi=90)
        stream.seek(0)
        with Image.open(stream) as frame:
            frames.append(frame.convert("RGB"))
    plt.close(figure)
    movie_path = output / "deter-monthly-alerts.gif"
    frames[0].save(movie_path, save_all=True, append_images=frames[1:], duration=320, loop=0)
    return plot_path, movie_path, len(frames)
