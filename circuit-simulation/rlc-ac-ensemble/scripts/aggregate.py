"""Verify every AC sample and render representative response comparisons."""

import csv
import gzip
import hashlib
import io
import itertools
import json
import math
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from rlc import ATOL, BATCHES, CASES_PER_BATCH, RTOL, SWEEP_POINTS, response

REPRESENTATIVE = (0, 975, 2048, 3120, 4095)
manifest = json.loads(Path("manifest.json").read_text())
if len(manifest) != BATCHES * CASES_PER_BATCH:
    raise ValueError("Unexpected prepared manifest size")
batch_rows = []
timing_rows = []
selected = {}
for batch in range(BATCHES):
    stem = f"batch-{batch:03d}"
    report = json.loads(Path(f"{stem}.json").read_text())
    artifact = Path(f"{stem}.csv.gz")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    first = batch * CASES_PER_BATCH
    planned = list(range(first, first + CASES_PER_BATCH))
    if report["batch"] != batch or report["sha256"] != digest:
        raise ValueError(f"Invalid batch evidence for {batch}")
    if [item["circuit"] for item in report["circuits"]] != planned:
        raise ValueError(f"Unexpected result inventory in batch {batch}")
    verified_ids = []
    peak = 0.0
    with gzip.open(artifact, "rt", newline="") as stream:
        for key, sample_group in itertools.groupby(csv.DictReader(stream), key=lambda row: int(row["circuit"])):
            if key not in planned:
                raise ValueError(f"Unscheduled circuit {key} in batch {batch}")
            circuit = manifest[key]
            if circuit["circuit"] != key or circuit["batch"] != batch:
                raise ValueError(f"Manifest mismatch for circuit {key}")
            rows = list(sample_group)
            frequencies = [float(row["frequency_hz"]) for row in rows]
            resonance = 1 / (math.tau * math.sqrt(circuit["L_henry"] * circuit["C_farad"]))
            if ([row["kind"] for row in rows] != ["sweep"] * SWEEP_POINTS + ["resonance"]
                    or not np.allclose(frequencies[:-1], np.geomspace(1, 1e8, SWEEP_POINTS),
                                       rtol=1e-10, atol=0)
                    or not math.isclose(frequencies[-1], resonance, rel_tol=1e-12)):
                raise ValueError(f"Unexpected frequency grid for circuit {key}")
            for row, frequency in zip(rows, frequencies):
                expected = response(frequency, circuit["R_ohm"], circuit["L_henry"], circuit["C_farad"])
                measured = complex(float(row["real"]), float(row["imaginary"]))
                ratio = abs(measured - expected) / (ATOL + RTOL * abs(expected))
                if not math.isfinite(ratio) or ratio > 1:
                    raise ValueError(f"Tolerance exceeded in circuit {key}")
                peak = max(peak, ratio)
            if key in REPRESENTATIVE:
                selected[key] = rows[:-1]
            verified_ids.append(key)
    if verified_ids != planned:
        raise ValueError(f"Duplicate or missing circuit response in batch {batch}")
    batch_rows.append({"batch": batch, "circuits": len(planned),
                       "samples": len(planned) * (SWEEP_POINTS + 1),
                       "max_error_fraction": peak, "response_sha256": digest})
    timing_rows.append({"batch": batch, "elapsed_seconds": report["elapsed_seconds"],
                        "startup_control_median_seconds": statistics.median(report["startup_control_seconds"]),
                        "ngspice_wall_seconds": sum(row["ngspice_wall_seconds"] for row in report["circuits"]),
                        "solver_analysis_seconds": sum(row["solver_analysis_seconds"] for row in report["circuits"]),
                        "parse_validate_seconds": sum(row["parse_validate_seconds"] for row in report["circuits"]),
                        "parent_peak_rss_kib": report["max_rss_kib"]})

if tuple(sorted(selected)) != REPRESENTATIVE:
    raise ValueError("Missing representative circuits")
representative_rows = [row for index in REPRESENTATIVE for row in selected[index]]
for name, rows in (("rlc-batches.csv", batch_rows), ("rlc-timing.csv", timing_rows),
                   ("rlc-representative.csv", representative_rows)):
    with Path(name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

frames = []
for index in REPRESENTATIVE:
    circuit = manifest[index]
    rows = selected[index]
    frequencies = np.array([float(row["frequency_hz"]) for row in rows])
    simulation = np.array([complex(float(row["real"]), float(row["imaginary"])) for row in rows])
    analytic = np.array([response(f, circuit["R_ohm"], circuit["L_henry"], circuit["C_farad"])
                         for f in frequencies])
    figure, (gain, phase) = plt.subplots(1, 2, figsize=(10, 4.3), layout="constrained")
    figure.suptitle(f"Series RLC · circuit {index} · "
                    f"R={circuit['R_ohm']:.3g} Ω, L={circuit['L_henry']:.3g} H, C={circuit['C_farad']:.3g} F")
    for values, color, line, label in ((analytic, "#1f4668", "-", "Analytic"),
                                       (simulation, "#a2562b", "--", "ngspice")):
        gain.semilogx(frequencies, 20 * np.log10(np.abs(values)), line, color=color, label=label)
        phase.semilogx(frequencies, np.angle(values, deg=True), line, color=color, label=label)
    gain.set(title="Gain", xlabel="Frequency (Hz)", ylabel="Magnitude (dB)")
    phase.set(title="Phase", xlabel="Frequency (Hz)", ylabel="Phase (degrees)", ylim=(-190, 10))
    for axis in (gain, phase):
        axis.grid(alpha=0.2)
        axis.legend()
    if index == REPRESENTATIVE[2]:
        figure.savefig("rlc-bode.png", dpi=115)
    with io.BytesIO() as buffer:
        figure.savefig(buffer, format="png", dpi=100)
        buffer.seek(0)
        with Image.open(buffer) as image:
            frames.append(image.convert("RGB"))
    plt.close(figure)
frames[0].save("rlc-bode.gif", save_all=True, append_images=frames[1:],
               duration=1250, loop=0, disposal=2)
with Image.open("rlc-bode.gif") as animation:
    if animation.n_frames != len(REPRESENTATIVE):
        raise ValueError("Unexpected number of Bode frames")
    for index in range(animation.n_frames):
        animation.seek(index)
        animation.load()

outputs = ("rlc-batches.csv", "rlc-representative.csv", "rlc-bode.png", "rlc-bode.gif")
validation = {"passed": True, "batches": len(batch_rows), "circuits": sum(row["circuits"] for row in batch_rows),
              "samples": sum(row["samples"] for row in batch_rows), "gif_frames": len(frames),
              "max_error_fraction": max(row["max_error_fraction"] for row in batch_rows),
              "sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in outputs}}
Path("validation.json").write_text(json.dumps(validation, indent=2) + "\n")
