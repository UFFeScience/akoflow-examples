"""Capture and check fixed calendar partitions of the official anonymous DETER layer."""

import argparse
from datetime import date, datetime, timezone
import gzip
from hashlib import sha256
import json
from pathlib import Path
from time import sleep
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ORIGIN = "https://terrabrasilis.dpi.inpe.br/geoserver/ows"
LAYER = "deter-amz:deter_amz"
PAGE_SIZE = 2000


def download(start, end, offset):
    query = urlencode({
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": LAYER, "count": PAGE_SIZE, "startIndex": offset,
        "sortBy": "gid A,view_date A,mun_geocod A,classname A,path_row A", "outputFormat": "application/json",
        "CQL_FILTER": f"view_date >= '{start}' AND view_date < '{end}'",
    })
    for attempt in range(4):
        try:
            with urlopen(f"{ORIGIN}?{query}", timeout=60) as response:
                return json.load(response)
        except (URLError, TimeoutError, json.JSONDecodeError):
            if attempt == 3:
                raise
            sleep(2 ** attempt)


def month(start, end, folder):
    path = folder / f"{start:%Y-%m}.geojson.gz"
    evidence = path.with_suffix(".json")
    if path.exists() and evidence.exists():
        metadata = json.loads(evidence.read_text())
        if sha256(path.read_bytes()).hexdigest() == metadata["sha256"]:
            return metadata
    records = []
    fingerprints = set()
    expected = None
    while expected is None or len(records) < expected:
        page = download(start, end, len(records))
        count = page["numberMatched"]
        if expected is None:
            expected = count
        if count != expected or page["numberReturned"] != len(page["features"]):
            raise ValueError(f"{start}: source count changed during pagination")
        if not page["features"] and len(records) < expected:
            raise ValueError(f"{start}: incomplete page at offset {len(records)}")
        for feature in page["features"]:
            row = feature["properties"]
            key = row["gid"]
            observed = date.fromisoformat(row["view_date"])
            geometry = feature["geometry"]
            canonical = json.dumps(feature, sort_keys=True, separators=(",", ":"), allow_nan=False)
            fingerprint = sha256(canonical.encode()).digest()
            if fingerprint in fingerprints or not start <= observed < end:
                raise ValueError(f"{start}: duplicate feature content or out-of-window date for {key}")
            if geometry is None or geometry["type"] not in {"Polygon", "MultiPolygon"}:
                raise ValueError(f"{start}: invalid geometry for {key}")
            fingerprints.add(fingerprint)
            records.append(feature)
        sleep(0.2)
    if len(records) != expected:
        raise ValueError(f"{start}: expected {expected} records, received {len(records)}")
    document = {"type": "FeatureCollection", "features": records}
    encoded = gzip.compress(json.dumps(document, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False, allow_nan=False).encode(), mtime=0)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)
    metadata = {"start": str(start), "end": str(end), "features": len(records),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "sha256": sha256(encoded).hexdigest(), "bytes": len(encoded), "name": path.name}
    evidence.write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    args.folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    for year in range(2019, 2025):
        for number in range(1, 13):
            start = date(year, number, 1)
            end = date(year + (number == 12), number % 12 + 1, 1)
            entry = month(start, end, args.folder)
            manifest.append(entry)
            print(json.dumps(entry), flush=True)
    (args.folder / "manifest.json").write_text(json.dumps({
        "source": ORIGIN, "layer": LAYER, "license": "CC BY-SA 4.0", "months": manifest,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
