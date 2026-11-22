#!/usr/bin/env python3
"""Networked preparation step for the frozen OceanBench two-week slice."""
import hashlib
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://s3.waw3-1.cloudferro.com"
BUCKET = "oceanbench-bucket"
PREFIXES = [
    "public/ml-forecast-outputs/glonet/20240103.zarr/",
    "public/ml-forecast-outputs/glonet/20240110.zarr/",
    "public/glorys_1degree_2024_V2/20240103.zarr/",
    "public/glorys_1degree_2024_V2/20240110.zarr/",
    "public/glo12_1degree_2024_V2/20240103.zarr/",
    "public/glo12_1degree_2024_V2/20240110.zarr/",
    "public/GLO12_MDT/GLO-MFC_001_024_mdt_1_deg.zarr/",
    "public/ocean_mask/oceanbench-ocean-mask-v2.zarr/",
] + [f"public/observations2024-v2/202401{day:02d}.zarr/" for day in range(3, 20)]


def list_prefix(prefix):
    token = None
    while True:
        query = {"list-type": "2", "prefix": prefix}
        if token:
            query["continuation-token"] = token
        url = f"{BASE}/{BUCKET}?{urllib.parse.urlencode(query)}"
        with urllib.request.urlopen(url, timeout=120) as response:
            root = ET.fromstring(response.read())
        ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
        for item in root.findall("s:Contents", ns):
            yield {
                "key": item.findtext("s:Key", namespaces=ns),
                "size": int(item.findtext("s:Size", namespaces=ns)),
                "etag": item.findtext("s:ETag", namespaces=ns).strip('"'),
                "last_modified": item.findtext("s:LastModified", namespaces=ns),
            }
        token = root.findtext("s:NextContinuationToken", namespaces=ns)
        if not token:
            return


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    inputs = Path(__file__).resolve().parent / "inputs"
    root = inputs / "snapshot"
    root.mkdir(parents=True, exist_ok=True)
    objects = []
    for prefix in PREFIXES:
        found = list(list_prefix(prefix))
        if not found:
            raise RuntimeError(f"empty prefix: {prefix}")
        def fetch(item):
            target = root / item["key"]
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or target.stat().st_size != item["size"]:
                urllib.request.urlretrieve(f"{BASE}/{BUCKET}/{urllib.parse.quote(item['key'])}", target)
            if target.stat().st_size != item["size"]:
                raise RuntimeError(f"size mismatch: {item['key']}")
            return {**item, "sha256": sha256(target)}
        with ThreadPoolExecutor(max_workers=16) as pool:
            objects.extend(pool.map(fetch, found))
        print(f"prepared {prefix}: {len(found)} objects", flush=True)
    manifest = {
        "bucket": BUCKET,
        "endpoint": BASE,
        "prefixes": PREFIXES,
        "objects": sorted(objects, key=lambda row: row["key"]),
        "object_count": len(objects),
        "total_bytes": sum(row["size"] for row in objects),
        "identity": "S3 size + ETag + Last-Modified and downloaded SHA-256",
    }
    (inputs / "input-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    notebook = inputs / "glonet_1_degree_sample.global.report.ipynb"
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/mercator-ocean/oceanbench/61aea40e13689b3dbb0592a74dbf716f15882f5b/assets/glonet_1_degree_sample.global.report.ipynb",
        notebook,
    )
    expected = "dfa92abfe9ddc515dd37e2a58bc7cbede71471c6e9b913bcf54de38fa0b6913a"
    if sha256(notebook) != expected:
        raise RuntimeError("reference notebook digest mismatch")


if __name__ == "__main__":
    main()
