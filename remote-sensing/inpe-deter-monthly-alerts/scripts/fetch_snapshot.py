"""Fetch the frozen DETER and IBGE inputs at image build time."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
from time import sleep
from urllib.error import URLError
from urllib.request import urlopen


def fetch(url, path, expected):
    for attempt in range(4):
        try:
            with urlopen(url, timeout=40) as response:
                data = response.read()
            break
        except (URLError, TimeoutError):
            if attempt == 3:
                raise
            sleep(2 ** attempt)
    if sha256(data).hexdigest() != expected:
        raise ValueError(f"Input checksum mismatch for {path.name}")
    path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("configuration", type=Path)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    config = json.loads(args.configuration.read_text())
    manifest = json.loads((args.snapshot / "manifest.json").read_text())
    items = [*manifest["months"], config["boundary"]]
    names = [item["name"] for item in items]
    if len(names) != 73 or len(set(names)) != len(names) or any(Path(name).name != name for name in names):
        raise ValueError("Unexpected snapshot inventory")
    base = config["snapshot_base_url"]
    with ThreadPoolExecutor(max_workers=4) as workers:
        futures = [workers.submit(fetch, f"{base}/{item['name']}", args.snapshot / item["name"], item["sha256"])
                   for item in items]
        for future in futures:
            future.result()
    print(f"Verified {len(items)} frozen input archives")


if __name__ == "__main__":
    main()
