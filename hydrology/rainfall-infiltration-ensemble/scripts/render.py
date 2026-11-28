"""Render runoff and ponding across the frozen rainfall regimes."""

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from PIL import Image

from scenarios import RAIN


def render(rows, output):
    figure, axis = plt.subplots(figsize=(8, 4.7), layout="constrained")
    markers = axis.scatter([row["rain_mm_h"] for row in rows],
                           [row["mean_runoff_mm"] for row in rows],
                           c=[row["ponded_fraction"] for row in rows],
                           cmap="viridis", vmin=0, vmax=1, alpha=0.7, s=15)
    axis.set(title="Runoff across 512 soil-column batches", xlabel="Rain intensity (mm/h)",
             ylabel="Mean runoff after four hours (mm)", xticks=RAIN)
    figure.colorbar(markers, ax=axis, label="Fraction ponded during rainfall")
    figure.savefig(output / "rainfall-runoff.png", dpi=125)
    plt.close(figure)

    frames = []
    for rain in RAIN:
        selected = [row for row in rows if row["rain_mm_h"] == rain]
        figure, axis = plt.subplots(figsize=(8, 4.7), layout="constrained")
        markers = axis.scatter([row["conductivity_mm_h"] for row in selected],
                               [row["mean_runoff_mm"] for row in selected],
                               c=[row["ponded_fraction"] for row in selected],
                               cmap="viridis", vmin=0, vmax=1, alpha=0.7, s=20)
        axis.set(title=f"Rain intensity {rain} mm/h", xlabel="Nominal conductivity (mm/h)",
                 ylabel="Mean runoff after four hours (mm)", ylim=(-5, 365),
                 xticks=(4, 8, 16, 32))
        figure.colorbar(markers, ax=axis, label="Fraction ponded during rainfall")
        buffer = BytesIO()
        figure.savefig(buffer, format="png", dpi=95)
        plt.close(figure)
        buffer.seek(0)
        with Image.open(buffer) as frame:
            frames.append(frame.convert("RGB"))
    frames[0].save(output / "rainfall-runoff.gif", save_all=True, append_images=frames[1:],
                   duration=800, loop=0)
    return len(frames)
