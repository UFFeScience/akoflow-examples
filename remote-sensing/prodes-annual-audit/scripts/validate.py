"""Audit generated artifact contents and record their digests."""

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from PIL import Image

from reduce import SERIES, YEARS

with Path("prodes-annual.csv").open(newline="") as stream:
    rows = list(csv.DictReader(stream))

for region, (_, _, locations, references) in SERIES.items():
    records = [row for row in rows if row["region"] == region]
    if sorted(int(row["year"]) for row in records) != sorted(YEARS):
        raise ValueError(f"Invalid year coverage for {region}")
    for row in records:
        area = Decimal(row["area_km2"])
        year = int(row["year"])
        if int(row["location_count"]) != locations or not area.is_finite() or area < 0:
            raise ValueError(f"Invalid area or location count for {region} {year}")
        if year in references:
            reference, tolerance = references[year]
            if abs(area - reference) > tolerance:
                raise ValueError(f"Reference mismatch for {region} {year}")

if len(rows) != len(SERIES) * len(YEARS):
    raise ValueError("Unexpected extra rows")

with Image.open("prodes-annual.png") as figure:
    if figure.format != "PNG":
        raise ValueError("Expected a PNG figure")
    figure.verify()

with Image.open("prodes-annual.gif") as animation:
    if animation.format != "GIF" or animation.n_frames != len(YEARS):
        raise ValueError("Expected one GIF frame per year")
    for frame in range(animation.n_frames):
        animation.seek(frame)
        animation.load()

outputs = ("prodes-annual.csv", "prodes-annual.png", "prodes-annual.gif")
report = {
    "passed": True,
    "rows": len(rows),
    "frames": len(YEARS),
    "sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in outputs},
}
Path("validation.json").write_text(json.dumps(report, indent=2) + "\n")
