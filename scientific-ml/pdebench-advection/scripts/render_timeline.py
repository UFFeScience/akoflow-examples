import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

items = json.loads(Path(sys.argv[1]).read_text())
origin = min(item["startedAt"] for item in items)
overlap_start = max(
    item["startedAt"] for item in items
    if item["activity"] in ("infer-fno", "infer-unet")
)
overlap_finish = min(
    item["finishedAt"] for item in items
    if item["activity"] in ("infer-fno", "infer-unet")
)
overlap = max(0.0, overlap_finish - overlap_start)
figure, axis = plt.subplots(figsize=(11, 4.8))
colors = {"slot-0": "#111111", "slot-1": "#777777"}
for row, item in enumerate(items):
    start = item["startedAt"] - origin
    duration = item["finishedAt"] - item["startedAt"]
    axis.barh(row, duration, left=start, color=colors[item["resource"]], height=0.65)
    axis.text(start + 0.05, row, item["activity"], va="center", ha="left",
              color="white", fontsize=8)
if overlap:
    axis.axvspan(overlap_start - origin, overlap_finish - origin,
                 color="#e63946", alpha=0.18,
                 label=f"measured FNO/U-Net overlap: {overlap:.3f} s")
axis.set(
    yticks=range(len(items)),
    yticklabels=[item["resource"] for item in items],
    xlabel="seconds from first activity start",
    title="AkôFlow measured activity timeline — PDEBench advection audit",
)
axis.invert_yaxis()
axis.legend(loc="lower right", frameon=False)
figure.tight_layout()
figure.savefig(sys.argv[2], dpi=180)
plt.close(figure)
