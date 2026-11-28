"""Import the public microscopy URI and verify a clean reference execution."""

import argparse
import json
import os
import re
from pathlib import Path

from generate import PREFIX, configuration
from profile import import_workflow, run

PUBLICATION = "32488dc6-0e85-4957-8914-bdd2e29408ab"
WORKFLOW = f"{PREFIX}-ensemble-v1"
CASES = 768


def verify(uri, reference_path, evidence):
    reference = json.loads(reference_path.read_text())
    if reference["run"]["status"] != "completed" or reference["cases"] != CASES:
        raise ValueError("Expected the completed 768-case reference capture")
    evidence.mkdir(parents=True, exist_ok=True)
    receipt = evidence / "import.json"
    if receipt.exists():
        result = json.loads(receipt.read_text())
        if result["uri"] != uri:
            raise ValueError("Import receipt belongs to another URI")
    else:
        result = {"uri": uri, "workflow": import_workflow(uri)}
        receipt.write_text(json.dumps(result, indent=2) + "\n")
    if result["workflow"]["name"] != WORKFLOW:
        raise ValueError("The Hub imported an unexpected workflow")
    config_dir = evidence.resolve() / "configuration"
    config_dir.mkdir(exist_ok=True)
    configuration([f"case-{index:03d}" for index in range(CASES)], directory=config_dir)
    os.environ["AKOFLOW_CONFIG_DIR"] = str(config_dir)
    os.environ["AKOFLOW_USE_IMPORTED_WORKFLOW"] = "1"
    run(evidence, WORKFLOW, CASES, 4, reference["digests"], require_build=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uri")
    parser.add_argument("reference", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(rf"akoflow://hub/publications/{PUBLICATION}/versions/[1-9][0-9]*", args.uri):
        parser.error("expected a versioned microscopy publication URI")
    verify(args.uri, args.reference, args.evidence)


if __name__ == "__main__":
    main()
