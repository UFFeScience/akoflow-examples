"""Summarize independently certified BFS traces and render the gallery."""

import csv
import hashlib
import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image

families = ("kronecker", "uniform")
records = []
panels = {}
for family in families:
    result = json.loads(Path(f"{family}.json").read_text())
    if not result["verified"] or result["control"] != [0, 1, 1, 2, -1, -1]:
        raise ValueError(f"Verification failed for {family}")
    if [item["scale"] for item in result["cases"]] != [14, 16]:
        raise ValueError(f"Wrong scale inventory for {family}")
    for case in result["cases"]:
        if len(case["sources"]) != 3:
            raise ValueError(f"Wrong source count for {family}")
        for source in case["sources"]:
            levels = source["levels"]
            records.extend({"family": family, "scale": case["scale"], "source": source["source"], **row}
                           for row in levels)
            if source is case["sources"][0] and case["scale"] == 16:
                panels[family] = levels

with Path("bfs-levels.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, records[0].keys(), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)

frames = []
steps = max(map(len, panels.values()))
for stop in range(1, steps + 1):
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.4), layout="constrained")
    figure.suptitle(f"GAP BFS adjacency checks through level {stop - 1}")
    for axis, (family, levels) in zip(axes, panels.items()):
        visible = levels[:stop]
        axis.plot([row["depth"] for row in visible], [row["top_down_checks"] for row in visible],
                  "o--", color="#7b675a", label="Top-down control")
        axis.plot([row["depth"] for row in visible], [row["gap_checks"] for row in visible],
                  "o-", color="#196b58", label="Direction-optimizing")
        for row in visible:
            if row["mode"] == "bu":
                axis.axvspan(row["depth"] - .3, row["depth"] + .3, color="#196b58", alpha=.12)
        maximum = max(max(row["gap_checks"], row["top_down_checks"]) for row in levels)
        axis.set(title=f"{family.title()} · scale 16", xlabel="BFS level", ylabel="Adjacency checks",
                 xlim=(-.4, steps - .6), ylim=(0, 1.08 * maximum), xticks=range(steps))
        axis.grid(alpha=.2)
        axis.legend(fontsize=8)
    if stop == steps:
        figure.savefig("bfs-levels.png", dpi=115)
    with io.BytesIO() as buffer:
        figure.savefig(buffer, format="png", dpi=100)
        buffer.seek(0)
        with Image.open(buffer) as frame:
            frames.append(frame.convert("RGB"))
    plt.close(figure)

frames[0].save("bfs-levels.gif", save_all=True, append_images=frames[1:],
               duration=850, loop=0, disposal=2)
with Image.open("bfs-levels.gif") as animation:
    if animation.n_frames != steps:
        raise ValueError("Animation frame count differs from the BFS trace")
    for index in range(steps):
        animation.seek(index)
        animation.load()

outputs = ("bfs-levels.csv", "bfs-levels.png", "bfs-levels.gif")
report = {"passed": True, "traversals_per_variant": 12, "rows": len(records), "gif_frames": steps,
          "sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in outputs}}
Path("validation.json").write_text(json.dumps(report, indent=2) + "\n")
