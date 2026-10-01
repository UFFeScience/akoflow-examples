#!/usr/bin/env python3
"""Deterministic, dependency-free executable for an AkôFlow showcase image."""
from __future__ import annotations
import argparse, csv, hashlib, json, pickle
from pathlib import Path

source_root = Path(__file__).resolve().parents[1]
container_config = Path("/app/scenario.json")
config_path = container_config if container_config.exists() else source_root / "data/input.json"
config = json.loads(config_path.read_text())

parser = argparse.ArgumentParser()
parser.add_argument("--stage", choices=config["stages"])
parser.add_argument("--output", default="/outputs" if container_config.exists() else str(source_root / "outputs"))
args = parser.parse_args()

stage = args.stage
if stage is not None and stage not in config["stages"]:
    raise SystemExit(f"unknown stage: {stage}")
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
selected_stages = [stage] if stage is not None else config["stages"]
record = {"showcase": config["slug"], "digest": digest, "stages": selected_stages, "status": "success"}
if stage is not None:
    (out / f"stage-{stage}.json").write_text(json.dumps({**record, "stage": stage}, indent=2) + "\n")
for name in config["artifacts"] if stage is None or stage == config["stages"][-1] else []:
    path = out / name
    if name.endswith(".json"):
        path.write_text(json.dumps({**record, "artifact": name}, indent=2) + "\n")
    elif name.endswith(".csv"):
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["candidate", "score", "selected"])
            writer.writeheader()
            writer.writerow({"candidate": config["slug"], "score": "1.000", "selected": "true"})
    elif name.endswith(".pkl"):
        path.write_bytes(pickle.dumps({**record, "artifact": name}, protocol=4))
    elif name.endswith(".html"):
        path.write_text("<!doctype html><title>AkôFlow report</title><h1>" + config["title"] + "</h1><pre>" + json.dumps(record, indent=2) + "</pre>")
    elif name.endswith(".md"):
        path.write_text("# " + config["title"] + "\n\n" + json.dumps(record, indent=2) + "\n")
    else:
        path.write_text(json.dumps({**record, "artifact": name}) + "\n")
if stage is None or stage == config["stages"][-1]:
    (out / "manifest.json").write_text(
        json.dumps({**record, "artifacts": config["artifacts"]}, indent=2) + "\n"
    )
