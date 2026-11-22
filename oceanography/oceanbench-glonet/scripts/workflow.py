import argparse
import hashlib
import json
from io import StringIO
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import oceanbench
import pandas as pd

DATES = [datetime.fromisoformat("2024-01-03"), datetime.fromisoformat("2024-01-10")]
ROOT = Path("/inputs/snapshot")
BRANCHES = {
    "glorys-state": "rmsd_of_variables_compared_to_glorys_reanalysis",
    "glorys-mld": "rmsd_of_mixed_layer_depth_compared_to_glorys_reanalysis",
    "glorys-geostrophic": "rmsd_of_geostrophic_currents_compared_to_glorys_reanalysis",
    "observations": "rmsd_of_variables_compared_to_observations",
    "glorys-lagrangian": "deviation_of_lagrangian_trajectories_compared_to_glorys_reanalysis",
    "glo12-state": "rmsd_of_variables_compared_to_glo12_analysis",
    "glo12-mld": "rmsd_of_mixed_layer_depth_compared_to_glo12_analysis",
    "glo12-geostrophic": "rmsd_of_geostrophic_currents_compared_to_glo12_analysis",
    "glo12-lagrangian": "deviation_of_lagrangian_trajectories_compared_to_glo12_analysis",
}
BRANCH_ORDER = tuple(BRANCHES)


def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def configure_local_snapshot():
    from oceanbench.core import challenger_datasets, ocean_mask
    from oceanbench.core.references import glo12, glorys, observations
    challenger_datasets._CLOUDFERRO_ML_FORECASTS_URL = str(ROOT / "public/ml-forecast-outputs")
    glorys._glorys_1_degree_path = lambda date: str(ROOT / f"public/glorys_1degree_2024_V2/{np.datetime_as_string(date, unit='D').replace('-', '')}.zarr")
    glo12._glo12_1_degree_path = lambda date: str(ROOT / f"public/glo12_1degree_2024_V2/{np.datetime_as_string(date, unit='D').replace('-', '')}.zarr")
    observations.observation_path = lambda date: str(ROOT / f"public/observations2024-v2/{pd.Timestamp(date).strftime('%Y%m%d')}.zarr")
    observations._mean_dynamic_topography_zarr_url = lambda resolution: str(ROOT / "public/GLO12_MDT/GLO-MFC_001_024_mdt_1_deg.zarr")
    ocean_mask.OCEAN_MASK_URL = str(ROOT / "public/ocean_mask/oceanbench-ocean-mask-v2.zarr")


def open_challenger():
    configure_local_snapshot()
    dataset = oceanbench.datasets.challenger.glonet_1_degree(DATES)
    expected = {"first_day_datetime": 2, "lead_day_index": 10, "depth": 21, "latitude": 168, "longitude": 360}
    if dict(dataset.sizes) != expected:
        raise RuntimeError(f"challenger dimensions differ: {dict(dataset.sizes)}")
    if dataset.attrs.get("source") != "MOI GLONET" or dataset.attrs.get("Conventions") != "CF-1.8":
        raise RuntimeError("challenger metadata differs")
    return dataset


def reference_tables():
    notebook=json.loads(Path("/inputs/glonet_1_degree_sample.global.report.ipynb").read_text())
    tables=[]
    for cell in notebook["cells"]:
        if "oceanbench.metrics." not in "".join(cell.get("source", [])):
            continue
        for result in cell.get("outputs", []):
            html=result.get("data", {}).get("text/html")
            if html:
                tables.append(pd.read_html(StringIO("".join(html)), index_col=0)[0])
    if len(tables) != 9: raise RuntimeError(f"expected 9 notebook tables, found {len(tables)}")
    return dict(zip(BRANCH_ORDER, tables))


def prepare(output):
    manifest = json.loads(Path("/inputs/input-manifest.json").read_text())
    if manifest["object_count"] != len(manifest["objects"]): raise RuntimeError("manifest count")
    for row in manifest["objects"]:
        path = ROOT / row["key"]
        if path.stat().st_size != row["size"] or sha256(path) != row["sha256"]:
            raise RuntimeError(f"input identity mismatch: {row['key']}")
    ds = open_challenger()
    oracle=reference_tables()
    dump(output / "reference.json", {branch:{"shape":list(table.shape),"values":[[None if pd.isna(v) else float(v) for v in row] for row in table.to_numpy()]} for branch,table in oracle.items()})
    dump(output / "protocol.json", {
        "oceanbench_version": oceanbench.__version__, "commit": "61aea40e13689b3dbb0592a74dbf716f15882f5b",
        "dates": [d.date().isoformat() for d in DATES], "region": "global", "dimensions": dict(ds.sizes),
        "source": ds.attrs["source"], "input_manifest_sha256": sha256("/inputs/input-manifest.json"),
        "network": "disabled during scientific activities", "metric_branches": BRANCHES,
    })


def metric(output, branch):
    if branch not in BRANCHES: raise ValueError(branch)
    ds = open_challenger()
    table = getattr(oceanbench.metrics, BRANCHES[branch])(ds, region="global")
    oracle=reference_tables()[branch]
    observed=table.to_numpy(dtype=float); expected=oracle.to_numpy(dtype=float)
    if observed.shape != expected.shape or not np.array_equal(np.round(observed,6), np.round(expected,6), equal_nan=True):
        delta=np.nanmax(np.abs(observed-expected)) if observed.shape == expected.shape else None
        raise RuntimeError(f"complete notebook table mismatch for {branch}: shapes {observed.shape}/{expected.shape}, max delta {delta}")
    path = output / "branches" / branch
    path.mkdir(parents=True, exist_ok=True)
    table.to_csv(path / "table.csv", float_format="%.12g")
    dump(path / "table.json", {"branch": branch, "function": BRANCHES[branch], "index": list(map(str, table.index)),
         "columns": list(map(str, table.columns)), "values": [[None if pd.isna(v) else float(v) for v in row] for row in table.to_numpy()],
         "reference_displayed_precision_match": True, "compared_cells": int(np.isfinite(expected).sum())})


def aggregate(output):
    tables = {}
    for branch in BRANCHES:
        tables[branch] = json.loads((output / "branches" / branch / "table.json").read_text())
    dump(output / "results.json", {"tables": tables, "table_count": len(tables)})


def render(output):
    data = json.loads((output / "results.json").read_text())
    fig, axes = plt.subplots(3, 3, figsize=(15, 11), constrained_layout=True)
    for ax, (branch, table) in zip(axes.flat, data["tables"].items()):
        values = np.asarray(table["values"], dtype=float)
        lead = min(10, values.shape[1])
        for row in values[:min(5, len(values))]: ax.plot(range(1, lead + 1), row[:lead], alpha=.8)
        ax.set(title=branch, xlabel="Lead day", ylabel="Published metric"); ax.grid(alpha=.2)
    fig.savefig(output / "metric-leads.png", dpi=160); plt.close(fig)
    obs = data["tables"]["observations"]; values = np.asarray(obs["values"], dtype=float)
    fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(np.isfinite(values), aspect="auto", cmap="gray_r")
    ax.set(title="Observation metric coverage", xlabel="Metric column", ylabel="Metric row")
    fig.tight_layout(); fig.savefig(output / "observation-coverage.png", dpi=160); plt.close(fig)


def validate(output):
    data = json.loads((output / "results.json").read_text()); errors=[]
    if data["table_count"] != 9: errors.append("metric-family coverage")
    if not all(table.get("reference_displayed_precision_match") for table in data["tables"].values()): errors.append("complete table comparison")
    sentinels = {"glorys-state": (0, 0, .074619), "glorys-mld": (0, 0, 44.358207),
                 "glo12-state": (0, 0, .026430), "glo12-mld": (0, 0, 40.866022)}
    for branch, (row, col, expected) in sentinels.items():
        actual=data["tables"][branch]["values"][row][col]
        if round(actual, 6) != expected: errors.append(f"sentinel {branch}: {actual}")
    artifacts={p.name:sha256(p) for p in (output/"results.json",output/"metric-leads.png",output/"observation-coverage.png")}
    dump(output/"validation.json", {"passed":not errors,"errors":errors,"acceptance":"notebook displayed precision (6 decimals)","artifacts":artifacts})
    if errors: raise RuntimeError(errors)


def main():
    p=argparse.ArgumentParser(); p.add_argument("stage",choices=["prepare","metric","aggregate","render","validate"])
    p.add_argument("--output",default="."); p.add_argument("--branch"); a=p.parse_args(); output=Path(a.output); output.mkdir(parents=True,exist_ok=True)
    {"prepare":lambda:prepare(output),"metric":lambda:metric(output,a.branch),"aggregate":lambda:aggregate(output),"render":lambda:render(output),"validate":lambda:validate(output)}[a.stage]()
if __name__ == "__main__": main()
