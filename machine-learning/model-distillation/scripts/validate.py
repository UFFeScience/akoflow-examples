#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
expected = json.loads((root / "expected" / "manifest.json").read_text())
actual_path = root / "outputs" / "manifest.json"
if not actual_path.exists():
    sys.exit("missing outputs/manifest.json; run ./run.sh first")
actual = json.loads(actual_path.read_text())
if actual["showcase"] != expected["showcase"] or actual["artifacts"] != expected["artifacts"] or actual["status"] != "success":
    sys.exit("manifest does not match expected contract")
missing = [name for name in expected["artifacts"] if not (root / "outputs" / name).is_file() or (root / "outputs" / name).stat().st_size == 0]
if missing:
    sys.exit("missing artifacts: " + ", ".join(missing))
config = json.loads((root / "data/input.json").read_text())
missing = [name for name in config["stages"] if not (root / "outputs" / f"stage-{name}.json").is_file()]
if missing:
    sys.exit("missing activity outputs: " + ", ".join(missing))
print("validated " + expected["showcase"])

