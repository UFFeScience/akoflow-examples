#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import os
import shutil
from pathlib import Path

import numpy as np

BANDS = "ugriz"
PERIODS = np.linspace(0.2, 0.9, 1000)
REFERENCE_PERIOD = 0.6224468350410461
EXPECTED_PERIOD = 0.6225225225225225
TOLERANCE = 0.001


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def prepare_image_inputs(out):
    from gatspy.datasets import RRLyraeGenerated

    out.mkdir(parents=True, exist_ok=True)
    gen = RRLyraeGenerated(1019544, random_state=0)
    # Preserve the independent RNG and call order from upstream Figure 5.
    rng = np.random.RandomState(0)
    nights = np.arange(180); rng.shuffle(nights); nights = nights[:60]
    t = 57000 + nights + 0.05 * rng.randn(60)
    dy = 0.06 + 0.01 * rng.randn(60)
    all_magnitudes = np.array([gen.generated(band, t, err=dy, corrected=False)
                               for band in BANDS])
    filts = np.take(list(BANDS), np.arange(60), mode="wrap")
    y = all_magnitudes[np.arange(60) % 5, np.arange(60)]
    rows = sorted(zip(t, y, dy, filts), key=lambda row: row[0])
    with open(out / "observations.csv", "w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["time_mjd", "magnitude", "uncertainty", "band"])
        writer.writerows(rows)
    np.save(out / "period-grid.npy", PERIODS, allow_pickle=False)
    data_home = Path(os.environ.get("ASTROML_DATA", Path.home() / "astroML_data")) / "Sesar2010"
    inputs = []
    for path in sorted(data_home.glob("*")):
        if path.is_file():
            inputs.append({"name": path.name, "bytes": path.stat().st_size, "sha256": digest(path)})
    write_json(out / "input-provenance.json", {
        "dataset": "Sesar et al. (2010) Stripe 82 RR Lyrae templates",
        "dataset_record": "https://doi.org/10.26093/cds/vizier.17080717",
        "mirror": "https://github.com/astroML/astroML-data/tree/main/datasets/S82_RRLyr",
        "object_id": 1019544, "seed": 0, "reference_period_days": float(gen.period),
        "upstream_archives_retained_in_image_only": inputs,
        "gatspy_revision": "71384b8d15531bc01a6b85250a35cd675edccf44",
    })


def load_observations(root):
    rows = list(csv.DictReader(open(root / "observations.csv")))
    return (np.array([float(r["time_mjd"]) for r in rows]),
            np.array([float(r["magnitude"]) for r in rows]),
            np.array([float(r["uncertainty"]) for r in rows]),
            np.array([r["band"] for r in rows]))


def prepare(out):
    source = Path("/opt/frozen-input")
    out.mkdir(parents=True, exist_ok=True)
    for name in ("observations.csv", "period-grid.npy", "input-provenance.json"):
        shutil.copy2(source / name, out / name)
    write_json(out / "scenario.json", {"object_id": 1019544, "seed": 0, "nights": 60,
        "season_days": 180, "bands": list(BANDS), "period_grid_days": [0.2, 0.9, 1000],
        "model": {"Nterms_base": 1, "Nterms_band": 0}})


def periodogram(root, out, band):
    from gatspy.periodic import LombScargleAstroML, LombScargleMultiband

    t, y, dy, filts = load_observations(root)
    periods = np.load(root / "period-grid.npy", allow_pickle=False)
    if band == "multiband":
        model = LombScargleMultiband(Nterms_base=1, Nterms_band=0).fit(t, y, dy, filts)
    else:
        mask = filts == band
        model = LombScargleAstroML().fit(t[mask], y[mask], dy[mask])
    power = model.periodogram(periods)
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / f"periodogram-{band}.npy", power, allow_pickle=False)
    peak = int(np.argmax(power))
    write_json(out / f"metrics-{band}.json", {"band": band, "samples": int(len(t) if band == "multiband" else np.sum(filts == band)),
        "best_period_days": float(periods[peak]), "peak_power": float(power[peak]),
        "array_sha256": digest(out / f"periodogram-{band}.npy")})


def aggregate(root, out):
    import matplotlib.pyplot as plt

    out.mkdir(parents=True, exist_ok=True)
    t, y, dy, filts = load_observations(root)
    periods = np.load(root / "period-grid.npy", allow_pickle=False)
    colors = dict(zip(BANDS, ["#7b2cbf", "#2a9d8f", "#e63946", "#457b9d", "#6c757d"]))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8), constrained_layout=True)
    for band in BANDS:
        power = np.load(root / f"periodogram-{band}.npy", allow_pickle=False)
        ax1.plot(periods, power, color=colors[band], alpha=.55, lw=1, label=band)
    multi = np.load(root / "periodogram-multiband.npy", allow_pickle=False)
    ax1.plot(periods, multi, color="black", lw=2.2, label="shared multiband")
    ax1.axvline(REFERENCE_PERIOD, color="#f4a261", ls="--", label="template period")
    ax1.set(xlabel="Trial period (days)", ylabel="Normalized power", title="Sparse RR Lyrae period recovery")
    ax1.legend(ncol=4, fontsize=8)
    phase = (t / REFERENCE_PERIOD) % 1
    for band in BANDS:
        mask = filts == band
        ax2.errorbar(phase[mask], y[mask], yerr=dy[mask], fmt="o", ms=4, color=colors[band], label=band)
    ax2.invert_yaxis(); ax2.set(xlabel="Phase", ylabel="Magnitude", title="Folded sparse light curve")
    fig.savefig(out / "scientific-result.png", dpi=160); plt.close(fig)


def animate(root, out):
    import matplotlib.pyplot as plt
    from PIL import Image

    out.mkdir(parents=True, exist_ok=True)
    periods = np.load(root / "period-grid.npy", allow_pickle=False)
    power = np.load(root / "periodogram-multiband.npy", allow_pickle=False)
    frames = []
    for stop in np.linspace(40, len(periods), 30, dtype=int):
        fig, ax = plt.subplots(figsize=(7, 4)); ax.plot(periods[:stop], power[:stop], color="black")
        ax.axvline(REFERENCE_PERIOD, color="#f4a261", ls="--")
        ax.set(xlim=(periods[0], periods[-1]), ylim=(0, max(power) * 1.08), xlabel="Trial period (days)", ylabel="Power", title=f"Shared-period scan: {stop}/1000 trials")
        fig.canvas.draw(); frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()))
        plt.close(fig)
    frames[0].save(out / "period-scan.gif", save_all=True, append_images=frames[1:], duration=90, loop=0)


def validate(root, out):
    t, y, dy, filts = load_observations(root)
    metrics = {name: json.loads((root / f"metrics-{name}.json").read_text()) for name in [*BANDS, "multiband"]}
    recovered = metrics["multiband"]["best_period_days"]
    error = abs(recovered - REFERENCE_PERIOD)
    checks = {"observation_count": len(t) == 60, "band_counts": all(np.sum(filts == b) == 12 for b in BANDS),
        "finite": bool(np.all(np.isfinite(t)) and np.all(np.isfinite(y)) and np.all(np.isfinite(dy))),
        "positive_uncertainties": bool(np.all(dy > 0)), "period_tolerance": error <= TOLERANCE,
        "expected_grid_peak": abs(recovered - EXPECTED_PERIOD) < 1e-12,
        "scientific_figure": (root / "scientific-result.png").is_file(), "animation": (root / "period-scan.gif").is_file()}
    out.mkdir(parents=True, exist_ok=True)
    report = {"status": "pass" if all(checks.values()) else "fail", "checks": checks,
        "reference_period_days": REFERENCE_PERIOD, "recovered_period_days": recovered, "absolute_error_days": error,
        "tolerance_days": TOLERANCE, "metrics": metrics}
    write_json(out / "validation.json", report)
    inventory = []
    for path in sorted(root.glob("*")):
        if path.is_file(): inventory.append({"name": path.name, "bytes": path.stat().st_size, "sha256": digest(path)})
    write_json(out / "manifest.json", {"publication_key": "community-explorer-issue-1-rrlyrae", "validation": report["status"], "artifacts": inventory})
    if report["status"] != "pass": raise SystemExit("validation failed: " + json.dumps(checks))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("stage"); parser.add_argument("--output", default="."); parser.add_argument("--input", default="."); parser.add_argument("--band")
    args = parser.parse_args(); out, root = Path(args.output), Path(args.input)
    if args.stage == "prepare-image-inputs": prepare_image_inputs(out)
    elif args.stage == "prepare": prepare(out)
    elif args.stage == "periodogram": periodogram(root, out, args.band)
    elif args.stage == "aggregate": aggregate(root, out)
    elif args.stage == "animate": animate(root, out)
    elif args.stage == "validate": validate(root, out)
    else: raise SystemExit(f"unknown stage {args.stage}")


if __name__ == "__main__": main()
