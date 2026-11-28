"""Write the immutable task manifest for all workflow batches."""

import json
from pathlib import Path

from scenarios import batches

Path("manifest.json").write_text(json.dumps(list(batches()), sort_keys=True) + "\n")
