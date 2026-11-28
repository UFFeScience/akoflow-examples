"""Rerun an imported PAN workflow and compare all reference artifacts."""

import argparse
import json
import os
from pathlib import Path
import re
import urllib.request

from generate import WORKFLOW, configuration
from profile import run

CASES = 768


def verify(uri, reference_path, evidence):
    reference = json.loads(reference_path.read_bytes())
    if (reference["run"]["status"] != "completed"
            or reference["run"]["id"] != f"{WORKFLOW}-run-4"
            or reference["cases"] != CASES
            or len(reference["digests"]) != CASES + 5):
        raise ValueError("Expected the completed four-slot PAN reference")
    evidence.mkdir(parents=True, exist_ok=True)
    receipt = evidence / "import.json"
    if receipt.exists():
        result = json.loads(receipt.read_bytes())
    else:
        api = os.environ["AKOFLOW_API_URL"].rstrip("/")
        token = os.environ["AKOFLOW_API_TOKEN"]
        request = urllib.request.Request(
            f"{api}/hub/workflows/import/",
            data=json.dumps({"uri": uri}).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = {"uri": uri, "workflow": json.load(response)}
    if result["uri"] != uri or result["workflow"]["name"] != WORKFLOW:
        raise ValueError("Expected the PAN workflow from the requested URI")
    temporary = receipt.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n")
    temporary.replace(receipt)
    configuration([f"case-{index:03d}" for index in range(CASES)])
    os.environ["AKOFLOW_USE_IMPORTED_WORKFLOW"] = "1"
    run(evidence, WORKFLOW, CASES, 4, reference["digests"], require_build=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uri")
    parser.add_argument("reference", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"akoflow://hub/publications/[0-9a-f-]{36}/versions/[1-9][0-9]*", args.uri):
        parser.error("expected a versioned Hub publication URI")
    verify(args.uri, args.reference, args.evidence)
