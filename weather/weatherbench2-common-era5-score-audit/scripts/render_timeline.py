import json
from pathlib import Path

import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
items = json.loads((root / "evidence/measured-activities.json").read_text())
origin = min(item["startedAt"] for item in items)
colors = {"community-wb2-slot-0": "#151515", "community-wb2-slot-1": "#8b8b8b"}
fig, axis = plt.subplots(figsize=(11, 6.5))
for row, item in enumerate(items):
    name = item["activityId"]
    start = item["startedAt"] - origin
    duration = item["finishedAt"] - item["startedAt"]
    axis.barh(row, duration, left=start, height=.62, color=colors[item["resourceId"]], edgecolor="black")
    axis.text(start + duration + .08, row, f"{duration:.2f}s", ha="left", va="center", fontsize=7, color="black", weight="bold")
axis.set_yticks(range(len(items)), [item["activityId"].replace("community-weatherbench2-score-audit-", "") for item in items])
axis.invert_yaxis()
axis.set_xlabel("Seconds since first activity start")
axis.set_title("AkôFlow measured timeline — WeatherBench 2 score audit")
axis.grid(axis="x", alpha=.25)
fig.tight_layout()
fig.savefig(root / "evidence/measured-timeline.png", dpi=180)
plt.close(fig)
