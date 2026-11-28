"""Join the analytic branch results and render a checked gallery."""

import csv
import hashlib
import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image

gain = json.loads(Path("gain.json").read_text())
spectral = json.loads(Path("spectral.json").read_text())
assert len(gain["rows"]) == 5
assert [row["deleted"] for row in spectral["rows"]] == list(range(8))
fields = ("branch", "gain", "deleted", "retained_fraction", "snr", "si_sdr", "sd_sdr")
with Path("si-sdr-scores.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for branch, result in (("gain", gain), ("spectral", spectral)):
        writer.writerows({"branch": branch, **row} for row in result["rows"])

frames = []
for cutoff in range(1, 8):
    figure, (a, b) = plt.subplots(1, 2, figsize=(10, 4.4), layout="constrained")
    figure.suptitle("Signal distortion metrics on fixed synthetic signals")
    colors = {"snr": "#2756a5", "si_sdr": "#1a795a", "sd_sdr": "#aa542f"}
    spectral_rows = spectral["rows"][1:cutoff+1]
    for field, color in colors.items():
        label = field.replace("_", "-").upper()
        a.plot([r["gain"] for r in gain["rows"]], [r[field] for r in gain["rows"]],
               marker="o", color=color, label=label)
        b.plot([r["deleted"] for r in spectral_rows], [r[field] for r in spectral_rows],
               marker="o", color=color, label=label)
    a.set(xscale="log", xlabel="Applied gain", ylabel="Score (dB)", title="Gain sweep")
    a.set_xticks([0.25, 0.5, 1, 2, 4], ["0.25", "0.5", "1", "2", "4"])
    b.set(xlabel="Deleted frequency bins", title=f"Spectral loss through {cutoff} deletions",
          xticks=range(1, 8), ylim=(-20, 12), xlim=(0.7, 7.3))
    for axis in (a, b):
        axis.grid(alpha=0.24)
        axis.legend()
    if cutoff == 7:
        figure.savefig("si-sdr-scores.png", dpi=115)
    with io.BytesIO() as buffer:
        figure.savefig(buffer, format="png", dpi=100)
        buffer.seek(0)
        with Image.open(buffer) as image:
            frames.append(image.convert("RGB"))
    plt.close(figure)

frames[0].save("si-sdr-scores.gif", save_all=True, append_images=frames[1:],
               duration=850, loop=0, disposal=2)
with Image.open("si-sdr-scores.gif") as animation:
    assert animation.n_frames == 7
    for index in range(animation.n_frames):
        animation.seek(index)
        animation.load()

files = ("si-sdr-scores.csv", "si-sdr-scores.png", "si-sdr-scores.gif")
report = {"passed": True, "gain_cases": 5, "spectral_cases": 8, "gif_frames": 7,
          "endpoints": gain["endpoints"],
          "sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in files}}
Path("validation.json").write_text(json.dumps(report, indent=2) + "\n")
