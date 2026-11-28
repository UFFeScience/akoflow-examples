"""Import the published shear-wave URI and verify a complete run against its reference."""

import argparse
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

from generate import ROOT, WORKFLOW, configuration
from profile import API, TOKEN, check_manifest, projection, save, wait_for

PUBLICATION = "c6e8246e-6a4c-48ca-914b-50bceae65549"
RUN_ID = "community-lbm-shear-wave-hub-clean"


def import_workflow(uri):
    request = urllib.request.Request(
        f"{API}/hub/workflows/import/",
        data=json.dumps({"uri": uri}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def verify(uri, reference_path, directory):
    reference = json.loads(reference_path.read_text())
    if reference["run"]["status"] != "completed" or len(reference["activities"]) != 1026:
        raise ValueError("Expected a completed 1,026-activity reference capture")
    baseline = check_manifest(dict(reference, dataObjects=reference["artifacts"]))
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / "import.json"
    if receipt.exists():
        stored = json.loads(receipt.read_text())
        if stored["uri"] != uri:
            raise ValueError("Import receipt belongs to another URI")
        imported = stored["workflow"]
    else:
        imported = import_workflow(uri)
        receipt.write_text(json.dumps({"uri": uri, "workflow": imported}, indent=2) + "\n")
    if imported["name"] != WORKFLOW:
        raise ValueError("Hub imported an unexpected workflow")
    log_path = directory / "submission.log"
    if projection(RUN_ID) is None:
        configuration()
        env = dict(os.environ, AKOFLOW_SUBMIT="1", AKOFLOW_USE_IMPORTED_WORKFLOW="1",
                   AKOFLOW_RUN_ID=RUN_ID, AKOFLOW_PLAN_FILE="plan-4.yaml",
                   AKOFLOW_PLAN_ID="community-lbm-shear-wave-plan-4-v1")
        with log_path.open("a") as log:
            subprocess.run([ROOT / "run.sh"], env=env, stdout=log, stderr=log, check=True)
    if "Build required" not in log_path.read_text():
        raise ValueError("Preflight did not request image reconstruction")
    save(directory / "verified-run.json", wait_for(RUN_ID), 4, 1, baseline)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uri")
    parser.add_argument("reference", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(rf"akoflow://hub/publications/{PUBLICATION}/versions/[1-9][0-9]*", args.uri):
        parser.error("expected a versioned public shear-wave publication URI")
    verify(args.uri, args.reference, args.evidence)


if __name__ == "__main__":
    main()
