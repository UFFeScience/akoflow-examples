"""Audit one frozen calendar-month partition from INPE DETER."""

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
from hashlib import sha256
import json
from math import floor, fsum, isfinite, radians, sin
from pathlib import Path
import re

UF_PREFIX = {"AC": "12", "AM": "13", "AP": "16", "MA": "21", "MT": "51",
             "PA": "15", "RO": "11", "RR": "14", "TO": "17"}
CLASSES = {
    "CICATRIZ_DE_QUEIMADA", "CS_DESORDENADO", "CS_GEOMETRICO", "DEGRADACAO",
    "DESMATAMENTO_CR", "DESMATAMENTO_VEG", "MINERACAO",
}
EARTH_RADIUS_KM = 6371.0088
CELL_DEGREES = 0.25


def polygon_metrics(geometry):
    polygons = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        polygons = [polygons]
    if geometry["type"] not in {"Polygon", "MultiPolygon"}:
        raise ValueError(f"Unexpected geometry type: {geometry['type']}")
    areas = []
    latitudes, longitudes = [], []
    for polygon in polygons:
        rings = []
        for ring in polygon:
            if len(ring) < 4 or ring[0] != ring[-1] or len({tuple(point) for point in ring}) < 3:
                return None
            points = [(point[0], point[1]) for point in ring]
            if any(not (-180 <= lon <= 180 and -90 <= lat <= 90) for lon, lat in points):
                return None
            measure = fsum(
                (radians(lon_b) - radians(lon_a)) * (sin(radians(lat_b)) + sin(radians(lat_a)))
                for (lon_a, lat_a), (lon_b, lat_b) in zip(points, points[1:])
            )
            rings.append(abs(measure) * EARTH_RADIUS_KM ** 2 / 2)
            longitudes.extend(point[0] for point in points)
            latitudes.extend(point[1] for point in points)
        if not rings or rings[0] <= sum(rings[1:]):
            return None
        areas.append(rings[0] - sum(rings[1:]))
    if not areas:
        return None
    return sum(areas), (min(longitudes) + max(longitudes)) / 2, (min(latitudes) + max(latitudes)) / 2


def audit(snapshot, metadata):
    raw = (snapshot / metadata["name"]).read_bytes()
    if sha256(raw).hexdigest() != metadata["sha256"]:
        raise ValueError(f"Input checksum mismatch for {metadata['name']}")
    features = json.loads(gzip.decompress(raw))["features"]
    if len(features) != metadata["features"]:
        raise ValueError(f"Unexpected record count in {metadata['name']}")
    start, end = map(date.fromisoformat, (metadata["start"], metadata["end"]))
    issues = Counter()
    provider_ids = Counter()
    shapes = Counter()
    grid = Counter()
    groups = defaultdict(list)
    geometry_areas = []
    for item in features:
        properties = item["properties"]
        state, category = properties["uf"], properties["classname"]
        municipality = properties["mun_geocod"]
        observed = date.fromisoformat(properties["view_date"])
        reported = properties["areamunkm"]
        if not start <= observed < end or category not in CLASSES:
            raise ValueError(f"Unexpected date or class for {properties['gid']}")
        if not (isinstance(reported, (int, float)) and isfinite(reported) and reported >= 0):
            raise ValueError(f"Invalid source area for {properties['gid']}")
        if (not isinstance(municipality, str) or not re.fullmatch(r"\d{7}", municipality)
                or not municipality.startswith(UF_PREFIX.get(state, "?"))):
            issues["invalid_municipal_code"] += 1
        provider_ids[properties["gid"]] += 1
        groups[state, category].append(reported)
        geometry = item["geometry"]
        shapes[sha256(json.dumps(geometry, sort_keys=True, separators=(",", ":")).encode()).digest()] += 1
        metrics = polygon_metrics(geometry)
        if metrics is None:
            issues["invalid_geometry"] += 1
            continue
        area, lon, lat = metrics
        geometry_areas.append(area)
        grid[floor(lon / CELL_DEGREES), floor(lat / CELL_DEGREES)] += 1
    issues["reused_provider_ids"] = sum(count - 1 for count in provider_ids.values())
    issues["repeated_exact_geometries"] = sum(count - 1 for count in shapes.values())
    return {
        "month": metadata["start"][:7], "input_sha256": metadata["sha256"],
        "features": len(features), "flags": dict(sorted(issues.items())),
        "spherical_area_km2_valid_shapes": fsum(geometry_areas),
        "groups": [{"uf": state, "class": category, "feature_count": len(values),
                    "reported_area_km2": fsum(values)}
                   for (state, category), values in sorted(groups.items())],
        "grid": [[lon, lat, count] for (lon, lat), count in sorted(grid.items())],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("month")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.snapshot / "manifest.json").read_text())
    metadata, = [row for row in manifest["months"] if row["start"][:7] == args.month]
    result = audit(args.snapshot, metadata)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f"audit-{args.month}.json").write_text(
        json.dumps(result, allow_nan=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
