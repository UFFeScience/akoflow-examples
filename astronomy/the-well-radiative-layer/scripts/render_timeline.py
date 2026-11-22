import json
import sys
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

source, destination = sys.argv[1:3]
with open(source, encoding="utf-8") as handle:
    data = json.load(handle)
activities = data["activities"]
origin = min(item["startedAt"] for item in activities)
rows = sorted(activities, key=lambda item: item["startedAt"])
colors = dict(zip((f"community-well-slot-{index}" for index in range(4)),
                  ["#111111", "#555555", "#888888", "#BBBBBB"]))

figure, axis = plt.subplots(figsize=(11, 7))
for row, item in enumerate(rows):
    start = item["startedAt"] - origin
    duration = item["finishedAt"] - item["startedAt"]
    suffix = item["activityId"].replace("community-well-radiative-layer-v1-", "")
    resource = item["plannedResourceId"]
    axis.barh(row, duration, left=start, color=colors.get(resource, "#DDDDDD"), edgecolor="black")
    axis.text(start + 0.08, row, suffix, va="center", fontsize=8,
              color="white" if resource.endswith(("0", "1")) else "black")

axis.set_yticks([])
axis.set_xlabel("Seconds since first activity start")
axis.set_title("Measured AkôFlow timeline — four local CPU slots")
axis.grid(axis="x", alpha=0.25)
started = datetime.fromtimestamp(origin, timezone.utc).isoformat(timespec="milliseconds")
axis.text(0, -1.3, f"Run {data['run']['id']} · origin {started} · makespan {data['run']['makespanSeconds']:.3f} s", fontsize=8)
figure.tight_layout()
figure.savefig(destination, dpi=180)
