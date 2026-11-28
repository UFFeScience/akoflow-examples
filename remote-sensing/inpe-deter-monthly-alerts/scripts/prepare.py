"""Record the immutable source manifest used by this execution."""

import json
from pathlib import Path

manifest = json.loads(Path("/app/snapshot/manifest.json").read_text())
if len(manifest["months"]) != 72:
    raise ValueError("Unexpected DETER input inventory")
Path("deter-source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
