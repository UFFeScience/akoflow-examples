"""Check the fixed Sobol ensemble and summarize its convergence."""

import csv
import hashlib
import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from workflow import EXPONENTS, REFERENCES, manifest

tasks = manifest()
stored_manifest = json.loads(Path("manifest.json").read_text())
if tasks != stored_manifest:
    raise ValueError("Prepared seed manifest does not match the frozen assignment")

raw = []
timing = []
for task in tasks:
    index = task["index"]
    record = json.loads(Path(f"replicate-{index:03d}.json").read_text())
    measures = json.loads(Path(f"timing-{index:03d}.json").read_text())
    if record["task"] != task or measures["index"] != index:
        raise ValueError(f"Manifest mismatch for replicate {index}")
    reference = REFERENCES[task["integrand"]]
    prefixes = record["prefixes"]
    if record["reference"] != reference or [row["exponent"] for row in prefixes] != list(EXPONENTS):
        raise ValueError(f"Unexpected prefix inventory for replicate {index}")
    for row in prefixes:
        value = row["estimate"]
        lower, upper = (1, 2**16) if task["integrand"] == "smooth" else (0, 1)
        if row["count"] != 1 << row["exponent"] or not lower <= value <= upper:
            raise ValueError(f"Invalid estimate for replicate {index}")
        raw.append({**task, **row, "reference": reference, "error": value - reference})
    timing.append(measures)

summaries = []
for method in ("sobol", "pseudo"):
    for integrand in REFERENCES:
        for exponent in EXPONENTS:
            values = np.array([row["error"] for row in raw if
                               (row["method"], row["integrand"], row["exponent"])
                               == (method, integrand, exponent)])
            if len(values) != 32:
                raise ValueError("Each cell must have 32 independent replicate estimates")
            variance = float(values.var(ddof=1))
            summaries.append({"method": method, "integrand": integrand,
                              "count": 1 << exponent, "bias": float(values.mean()),
                              "rmse": float(np.sqrt(np.mean(values**2))), "variance": variance,
                              "standard_error": float(np.sqrt(variance / len(values)))})

for name, rows in (("replicates.csv", raw), ("convergence.csv", summaries),
                   ("replicate-timing.csv", timing)):
    with Path(name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

frames = []
for stop in EXPONENTS:
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.4), layout="constrained")
    figure.suptitle(f"Replicate RMSE through 2^{stop} samples per replicate")
    for axis, integrand in zip(axes, REFERENCES):
        series = [row for row in summaries if row["integrand"] == integrand]
        for method, color in (("sobol", "#196b58"), ("pseudo", "#a64b30")):
            visible = [row for row in series if row["method"] == method and row["count"] <= 1 << stop]
            axis.loglog([row["count"] for row in visible], [row["rmse"] for row in visible],
                        marker="o", color=color, label=method.title())
        magnitudes = [row["rmse"] for row in series if row["rmse"] > 0]
        axis.set(title=integrand.title(), xlabel="Samples per replicate", ylabel="RMSE",
                 xlim=(900, 1.2 * 2**20), ylim=(.7*min(magnitudes), 1.4*max(magnitudes)))
        axis.legend()
        axis.grid(alpha=.2)
    if stop == EXPONENTS[-1]:
        figure.savefig("convergence.png", dpi=115)
    with io.BytesIO() as buffer:
        figure.savefig(buffer, format="png", dpi=95)
        buffer.seek(0)
        with Image.open(buffer) as frame:
            frames.append(frame.convert("RGB"))
    plt.close(figure)

frames[0].save("convergence.gif", save_all=True, append_images=frames[1:],
               duration=650, loop=0, disposal=2)
with Image.open("convergence.gif") as animation:
    if animation.n_frames != len(EXPONENTS):
        raise ValueError("Incomplete convergence animation")
    for index in range(animation.n_frames):
        animation.seek(index)
        animation.load()

outputs = ("replicates.csv", "convergence.csv", "convergence.png", "convergence.gif")
report = {"passed": True, "replicates": len(tasks), "estimates": len(raw),
          "prefixes": len(EXPONENTS), "frames": len(EXPONENTS),
          "sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in outputs}}
Path("validation.json").write_text(json.dumps(report, indent=2) + "\n")
