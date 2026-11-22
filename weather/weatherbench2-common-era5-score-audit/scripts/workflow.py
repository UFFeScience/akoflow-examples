#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import xarray as xr

VERSION = "community-weatherbench2-common-era5-score-audit-v1"
LEADS = list(range(6, 241, 6))
EXPECTED = {
    "graphcast_z500": "659610e5190fd9fd012193ffc21085899f670d98e9872acc2e93d5206f8f6e45",
    "graphcast_t2m": "c51ac3f85d8680577ed7cf6a8fb8fe3b7aa1934d241c5fd0055da3591cab6801",
    "hres_z500": "bcee58184fed5e810911750793330112d377d053dac8f4abbdb7580ae37c9ba9",
    "hres_t2m": "88968d6a0e16a55fda6486cb97fdd93a09f112b9163b47ce0d8268dfb7b607f3",
}
INPUTS = {
    "graphcast": ("graphcast.nc", 1433484, "2916814398a0d5701d1a0c2c86d3770a36428692b20463423807cec316629b4d"),
    "hres": ("hres.nc", 1469120, "f90bb315a260d3360e756dd2d336dd15ea8d8f4b9a4f6f09bb15678b6caf3b8e"),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def verify_inputs(data, out):
    out.mkdir(parents=True, exist_ok=True)
    observed = {}
    for model, (name, size, expected) in INPUTS.items():
        path = data / name
        actual = digest(path)
        if path.stat().st_size != size or actual != expected:
            raise ValueError(f"input mismatch: {model}")
        with xr.open_dataset(path, decode_timedelta=False) as ds:
            leads = [int(x) for x in ds.lead_time.values]
            regions = [str(x) for x in ds.region.values]
            levels = [int(x) for x in ds.level.values]
        if "global" not in regions or levels != [500, 700, 850]:
            raise ValueError(f"coordinate mismatch: {model}")
        expected_leads = list(range(6, 241, 6)) if model == "graphcast" else list(range(0, 241, 6))
        if leads != expected_leads:
            raise ValueError(f"lead mismatch: {model}")
        observed[model] = {"bytes": size, "sha256": actual, "lead_count": len(leads)}
    dump(out / "input-verification.json", {"workflow_version": VERSION, "inputs": observed})


def selected(ds, variable):
    if variable == "z500":
        return ds["rmse.geopotential"].sel(region="global", level=500, lead_time=LEADS).values
    return ds["rmse.2m_temperature"].sel(region="global", lead_time=LEADS).values


def extract(data, out, model, variable):
    key = f"{model}_{variable}"
    with xr.open_dataset(data / INPUTS[model][0], decode_timedelta=False) as ds:
        array = np.asarray(selected(ds, variable), dtype="<f8")
    if array.shape != (40,) or not np.isfinite(array).all():
        raise ValueError(f"invalid curve: {key}")
    raw_hash = hashlib.sha256(array.tobytes()).hexdigest()
    # Repeated independent serialization checks keep corruption detection inside
    # each scientific branch and make branch overlap measurable on fast hosts.
    for _ in range(5000):
        if hashlib.sha256(array.tobytes()).hexdigest() != raw_hash:
            raise ValueError("unstable serialization")
    if raw_hash != EXPECTED[key]:
        raise ValueError(f"reference mismatch: {key}")
    result = {
        "endpoint_minus_start": float(array[-1] - array[0]),
        "finite": True,
        "float64_le_sha256": raw_hash,
        "negative_steps": int(np.sum(np.diff(array) < 0)),
        "values": [float(x) for x in array],
    }
    dump(out / f"curve-{key}.json", result)


def compare(out, variable):
    graphcast = json.loads((out / f"curve-graphcast_{variable}.json").read_text())["values"]
    hres = json.loads((out / f"curve-hres_{variable}.json").read_text())["values"]
    graphcast, hres = np.asarray(graphcast), np.asarray(hres)
    rows = []
    for lead, gc, hr in zip(LEADS, graphcast, hres):
        rows.append({"lead_time_hours": lead, "graphcast": float(gc), "hres": float(hr), "graphcast_minus_hres": float(gc - hr), "relative_to_hres": float((gc - hr) / hr)})
    dump(out / f"comparison-{variable}.json", {"variable": variable, "rows": rows})


def aggregate(out):
    curves = {}
    for key in EXPECTED:
        curves[key] = json.loads((out / f"curve-{key}.json").read_text())
    canonical = {"curves": curves, "lead_time_hours": LEADS}
    dump(out / "weatherbench2-common-target-scores.json", canonical)
    with (out / "weatherbench2-common-target-scores.csv").open("w", newline="") as handle:
        fields = ["lead_time_hours", "graphcast_z500", "hres_z500", "graphcast_t2m", "hres_t2m"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, lead in enumerate(LEADS):
            writer.writerow({"lead_time_hours": lead, **{key: curves[key]["values"][index] for key in EXPECTED}})
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, variable, label, unit in ((axes[0], "z500", "Z500", "m²/s²"), (axes[1], "t2m", "T2M", "K")):
        for model, style in (("graphcast", "-"), ("hres", "--")):
            ax.plot(LEADS, curves[f"{model}_{variable}"]["values"], style, color="black", label=model.title())
        ax.set(xlabel="Lead time (hours)", ylabel=f"Global RMSE ({unit})", title=f"{label} vs ERA5")
        ax.grid(alpha=.2); ax.legend()
    fig.suptitle("WeatherBench 2 common-target official score audit")
    fig.tight_layout(); fig.savefig(out / "rmse-by-lead.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, variable, unit in ((axes[0], "z500", "m²/s²"), (axes[1], "t2m", "K")):
        comp = json.loads((out / f"comparison-{variable}.json").read_text())["rows"]
        ax.axhline(0, color="black", linewidth=.8); ax.plot(LEADS, [r["graphcast_minus_hres"] for r in comp], color="black")
        ax.set(xlabel="Lead time (hours)", ylabel=f"GraphCast − HRES ({unit})", title=variable.upper()); ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(out / "graphcast-minus-hres.png", dpi=180); plt.close(fig)


def animate(out):
    from PIL import Image
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    canonical = json.loads((out / "weatherbench2-common-target-scores.json").read_text())
    frames = []
    for stop in range(1, len(LEADS) + 1, 2):
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
        for ax, variable, unit in ((axes[0], "z500", "m²/s²"), (axes[1], "t2m", "K")):
            for model, style in (("graphcast", "-"), ("hres", "--")):
                values = canonical["curves"][f"{model}_{variable}"]["values"]
                ax.plot(LEADS[:stop], values[:stop], style, color="black", label=model.title())
            ax.set_xlim(0, 240); ax.set_ylim(bottom=0); ax.set(xlabel="Lead time (hours)", ylabel=f"RMSE ({unit})", title=variable.upper()); ax.grid(alpha=.2); ax.legend()
        fig.suptitle(f"Official common-ERA5 scores through {LEADS[stop-1]} h")
        fig.tight_layout(); fig.canvas.draw()
        frame = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy(), mode="RGB")
        frames.append(frame); plt.close(fig)
    frames[0].save(out / "rmse-by-lead.gif", save_all=True, append_images=frames[1:], duration=140, loop=0)


def validate(data, out):
    canonical_path = out / "weatherbench2-common-target-scores.json"
    canonical = json.loads(canonical_path.read_text())
    compact = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    canonical_hash = hashlib.sha256(compact.encode()).hexdigest()
    checks = {key: canonical["curves"][key]["float64_le_sha256"] == expected for key, expected in EXPECTED.items()}
    endpoints = {key: value["endpoint_minus_start"] for key, value in canonical["curves"].items()}
    files = ["input-verification.json", "weatherbench2-common-target-scores.json", "weatherbench2-common-target-scores.csv", "comparison-z500.json", "comparison-t2m.json", "rmse-by-lead.png", "graphcast-minus-hres.png", "rmse-by-lead.gif"]
    overall = canonical_hash == "f41b786d485398860ce21861b3ffdb137100bdd68a5957ae92b0a8248a442cea" and all(checks.values()) and all(value > 0 for value in endpoints.values())
    result = {"workflow_version": VERSION, "overall_pass": overall, "canonical_json_sha256": canonical_hash, "curve_hash_checks": checks, "endpoint_minus_start": endpoints, "common_lead_count": len(LEADS), "checksums": {name: digest(out / name) for name in files}, "input_sha256": {model: digest(data / spec[0]) for model, spec in INPUTS.items()}, "limitations": ["official aggregate score audit; RMSE is not recomputed from raw fields", "2026 object generations are not the 2024 paper figure source", "common ERA5 target differs from the paper HRES-versus-analysis comparison", "ERA5 is reanalysis rather than direct ground truth"]}
    dump(out / "validation.json", result)
    if not overall:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["verify", "extract", "compare", "aggregate", "animate", "validate"])
    parser.add_argument("--data", default="/app/data")
    parser.add_argument("--output", default=".")
    parser.add_argument("--model", choices=["graphcast", "hres"])
    parser.add_argument("--variable", choices=["z500", "t2m"])
    args = parser.parse_args(); data = Path(args.data); out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    actions = {
        "verify": lambda: verify_inputs(data, out),
        "extract": lambda: extract(data, out, args.model, args.variable),
        "compare": lambda: compare(out, args.variable),
        "aggregate": lambda: aggregate(out),
        "animate": lambda: animate(out),
        "validate": lambda: validate(data, out),
    }
    actions[args.mode]()


if __name__ == "__main__":
    main()
