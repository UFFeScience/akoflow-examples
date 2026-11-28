"""Import the published particle random walk workflow and compare its clean-run checksums."""

import argparse
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

from generate import WORKFLOW, configuration
from profile import OUTPUTS, profile


def verify(uri, reference, directory):
    baseline = json.loads(reference.read_bytes())
    if (baseline["run"] != f"{WORKFLOW}-run-4"
            or baseline["completed_activities"] != 257
            or len(baseline["digests"]) != 264):
        raise ValueError("Expected the completed four-slot reference")
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / "import.json"
    if receipt.exists():
        imported = json.loads(receipt.read_bytes())
    else:
        endpoint = os.environ["AKOFLOW_API_URL"].rstrip("/")
        request = Request(f"{endpoint}/hub/workflows/import/",
                          data=json.dumps({"uri": uri}).encode(),
                          headers={"Authorization": f"Bearer {os.environ['AKOFLOW_API_TOKEN']}",
                                   "Content-Type": "application/json"})
        with urlopen(request, timeout=60) as response:
            imported = {"uri": uri, "workflow": json.load(response)}
    if imported["uri"] != uri or imported["workflow"]["name"] != WORKFLOW:
        raise ValueError("Unexpected workflow or publication URI")
    temporary = receipt.with_suffix(".tmp")
    temporary.write_text(json.dumps(imported, indent=2) + "\n")
    temporary.replace(receipt)
    config = directory.resolve() / "configuration"
    config.mkdir(exist_ok=True)
    batches = sorted(Path(name).stem for name in baseline["digests"] if name not in OUTPUTS)
    if len(batches) != 256:
        raise ValueError("Expected 256 independent batch outputs")
    configuration(batches, directory=config)
    os.environ["AKOFLOW_CONFIG_DIR"] = str(config)
    os.environ["AKOFLOW_USE_IMPORTED_WORKFLOW"] = "1"
    rerun = profile(directory, 4, require_build=True)
    if rerun["digests"] != baseline["digests"]:
        raise ValueError("Clean run differs from the reference")
    rerun["uri"] = uri
    rerun["matching_artifact_checksums"] = len(rerun["digests"])
    (directory / "clean-run.json").write_text(json.dumps(rerun, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uri")
    parser.add_argument("reference", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"akoflow://hub/publications/[0-9a-f-]{36}/versions/[1-9][0-9]*", args.uri):
        parser.error("expected a versioned Hub URI")
    verify(args.uri, args.reference, args.directory)
