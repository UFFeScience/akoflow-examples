"""Validate and reduce one official TerraBrasilis dashboard snapshot."""

import argparse
import gzip
import hashlib
import json
from decimal import Decimal
from pathlib import Path

YEARS = set(range(2020, 2026))
SERIES = {
    "amazon": (
        "PRODES LEGAL AMAZON",
        "b906b595f4797130a967a7baaa51263f69080b47b3374c5741294ac68f18bcae",
        9,
        {2024: (Decimal("6518"), Decimal(0)), 2025: (Decimal("5731"), Decimal(0))},
    ),
    "cerrado": (
        "PRODES CERRADO",
        "1ff4ad9122988e7ecdf6b74d1d49a99dfd69e747ad5c6f248f2f9743b63e809e",
        13,
        {2024: (Decimal("8174"), Decimal("0.5"))},
    ),
}


def reduce_series(region: str, snapshot: bytes) -> list[dict]:
    name, digest, count, references = SERIES[region]
    if hashlib.sha256(snapshot).hexdigest() != digest:
        raise ValueError(f"Unexpected SHA-256 for {region}")
    dataset = json.loads(snapshot, parse_float=Decimal)
    if dataset["name"] != name:
        raise ValueError(f"Unexpected dataset name for {region}")
    rows = {}
    for period in dataset["periods"]:
        year = period["endDate"]["year"]
        if year not in YEARS:
            continue
        if (
            year in rows
            or period["startDate"] != {"year": year - 1, "month": 8, "day": 1}
            or period["endDate"] != {"year": year, "month": 7, "day": 31}
        ):
            raise ValueError(f"Unexpected reporting period for {region} {year}")
        locations = {}
        for feature in period["features"]:
            if feature["loi"] != 1:
                continue
            location = feature["loiname"]
            areas = [Decimal(item["area"]) for item in feature["areas"] if item["type"] == 1]
            if location in locations or len(areas) != 1 or not areas[0].is_finite() or areas[0] < 0:
                raise ValueError(f"Invalid location {location} for {region} {year}")
            locations[location] = areas[0]
        if len(locations) != count:
            raise ValueError(f"Expected {count} locations for {region} {year}")
        total = sum(locations.values(), Decimal(0))
        if year in references:
            reference, tolerance = references[year]
            if abs(total - reference) > tolerance:
                raise ValueError(f"Published reference mismatch for {region} {year}: {total}")
        rows[year] = {"year": year, "area_km2": str(total), "location_count": count}
    if rows.keys() != YEARS:
        raise ValueError(f"Incomplete reporting years for {region}")
    return [rows[year] for year in sorted(rows)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("region", choices=SERIES)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = reduce_series(args.region, gzip.decompress(args.input.read_bytes()))
    args.output.write_text(json.dumps({"region": args.region, "series": rows}, indent=2) + "\n")
