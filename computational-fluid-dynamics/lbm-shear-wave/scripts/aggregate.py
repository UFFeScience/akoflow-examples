"""Check the full shear-wave ensemble and render the measured field."""

import argparse
import csv
import gzip
import hashlib
import io
import json
from math import isclose, isfinite, log
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from PIL import Image


def read_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def validate(manifest, data, output):
    ids = {f"case-{row['id']}" for row in manifest}
    expected = {f"{key}-{suffix}.csv" for key in ids for suffix in ("metrics", "trace")}
    actual = {file.name for file in data.glob("case-*.csv")}
    if actual != expected | {"case-127-field.csv"}:
        raise ValueError("Incomplete or unexpected case artifacts")
    metrics = []
    with (output / "amplitudes.csv.gz").open("wb") as stream, gzip.GzipFile(
        fileobj=stream, mode="wb", mtime=0, filename=""
    ) as archive, io.TextIOWrapper(archive, encoding="utf-8", newline="") as text:
        writer = csv.writer(text, lineterminator="\n")
        writer.writerow(("id", "step", "mode_amplitude", "mean_density", "mean_momentum_x", "mean_momentum_y"))
        for scenario in manifest:
            case = f"case-{scenario['id']}"
            metric, = read_rows(data / f"{case}-metrics.csv")
            if any(metric[key] != value for key, value in scenario.items()):
                raise ValueError(f"{case}: manifest mismatch")
            trace = read_rows(data / f"{case}-trace.csv")
            steps = int(metric["steps"])
            if [int(row["step"]) for row in trace] != list(range(steps + 1)):
                raise ValueError(f"{case}: incomplete steps")
            mass = max(abs(float(row["mean_density"]) - 1) for row in trace)
            momentum = max(abs(float(row[axis])) for row in trace
                           for axis in ("mean_momentum_x", "mean_momentum_y"))
            amplitude = [float(row["mode_amplitude"]) for row in trace]
            if (not all(map(isfinite, amplitude)) or mass >= 1e-11 or momentum >= 1e-12):
                raise ValueError(f"{case}: non-finite state or failed conservation")
            if float(metric["initial_amplitude"]) == 0:
                if max(map(abs, amplitude)) >= 1e-14:
                    raise ValueError("Rest control acquired a shear mode")
            else:
                rate = log(amplitude[32] / amplitude[-1]) / (steps - 32)
                if (not isclose(rate, float(metric["measured_rate"]), rel_tol=1e-10)
                        or abs(rate / float(metric["discrete_rate"]) - 1) >= 1e-6
                        or abs(rate / float(metric["continuum_rate"]) - 1) >= 0.05):
                    raise ValueError(f"{case}: inconsistent decay rate")
            metrics.append(metric)
            writer.writerows((scenario["id"], *row.values()) for row in trace)
    with (output / "case-metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=metrics[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(metrics)


def render(field, output):
    rows = read_rows(field)
    steps = max(int(row["step"]) for row in rows) + 1
    width = max(int(row["y"]) for row in rows) + 1
    coordinates = [(int(row["step"]), int(row["y"])) for row in rows]
    if coordinates != [(step, y) for step in range(steps) for y in range(width)]:
        raise ValueError("Representative shear field is incomplete")
    values = [float(row["mean_velocity_x"]) for row in rows]
    if not all(map(isfinite, values)):
        raise ValueError("Representative shear field contains non-finite values")
    grid = [values[index:index+width] for index in range(0, len(values), width)]
    limit = max(map(abs, values))

    fig, axis = plt.subplots(figsize=(9, 5), layout="constrained")
    image = axis.imshow(grid, aspect="auto", origin="lower", cmap="coolwarm",
                        vmin=-limit, vmax=limit, extent=(0, width - 1, 0, steps - 1))
    axis.set(xlabel="Transverse node", ylabel="Time step", title="Measured periodic shear-wave decay")
    fig.colorbar(image, ax=axis, label="Mean streamwise velocity (lattice units)")
    fig.savefig(output / "shear-space-time.png", dpi=130)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8, 4), layout="constrained")
    line, = axis.plot(range(width), grid[0], color="#2b6684")
    axis.set(xlabel="Transverse node", ylabel="Mean streamwise velocity (lattice units)",
             ylim=(-limit*1.05, limit*1.05))
    frames = []
    indices = [round(index*(steps-1)/11) for index in range(12)]
    for step in indices:
        line.set_ydata(grid[step])
        axis.set_title(f"Periodic shear wave · step {step}")
        with io.BytesIO() as buffer:
            fig.savefig(buffer, format="png", dpi=100)
            buffer.seek(0)
            with Image.open(buffer) as frame:
                frames.append(frame.convert("RGB"))
    plt.close(fig)
    frames[0].save(output / "shear-decay.gif", save_all=True, append_images=frames[1:],
                   duration=550, loop=0)
    return len(frames)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--kernel", type=Path, default=Path("/app/shear-wave"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_text = subprocess.check_output([args.kernel.resolve(), "--manifest"], text=True)
    manifest = list(csv.DictReader(io.StringIO(manifest_text)))
    if len(manifest) != 1025 or len({row["id"] for row in manifest}) != 1025:
        raise ValueError("Expected all 1,024 scientific cases and the rest control")
    validate(manifest, args.input, args.output)
    frames = render(args.input / "case-127-field.csv", args.output)
    names = ("amplitudes.csv.gz", "case-metrics.csv", "shear-space-time.png", "shear-decay.gif")
    hashes = {name:hashlib.sha256((args.output / name).read_bytes()).hexdigest() for name in names}
    report = {"passed": True, "cases": 1024, "restControls": 1, "animationFrames": frames,
              "caseManifestSHA256": hashlib.sha256(manifest_text.encode()).hexdigest(), "sha256": hashes}
    (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
