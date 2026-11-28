"""Validate frozen archives and compute an independent SQL reference."""

import argparse
from collections import Counter
import csv
from datetime import date
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sqlite3


def load_month(db, folder, metadata):
    archive = (folder / metadata["name"]).read_bytes()
    if sha256(archive).hexdigest() != metadata["sha256"]:
        raise ValueError(f"SHA-256 mismatch for {metadata['name']}")
    features = json.loads(gzip.decompress(archive))["features"]
    if len(features) != metadata["features"]:
        raise ValueError(f"Unexpected feature count for {metadata['name']}")
    start, end = map(date.fromisoformat, (metadata["start"], metadata["end"]))
    records = []
    for feature in features:
        row = feature["properties"]
        observed = date.fromisoformat(row["view_date"])
        if not start <= observed < end:
            raise ValueError(f"Feature outside partition: {row['gid']}")
        digest = sha256(json.dumps(feature, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        records.append((metadata["start"][:7], row["gid"], row["uf"], row["classname"],
                        row["mun_geocod"], row["areamunkm"], digest))
    db.executemany("INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?)", records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    month_files = sorted(args.folder.glob("*.geojson.json"))
    if not month_files:
        raise ValueError("No completed months")
    months = [json.loads(path.read_text()) for path in month_files]
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(":memory:") as db:
        db.execute("""CREATE TABLE records (
                      month TEXT, gid TEXT, uf TEXT, class TEXT, municipality TEXT,
                      reported_area_km2 REAL, content_sha256 TEXT UNIQUE)""")
        for metadata in months:
            load_month(db, args.folder, metadata)
        query = """SELECT month, uf, class, COUNT(*) AS feature_count,
                          SUM(reported_area_km2) AS reported_area_km2
                   FROM records GROUP BY month, uf, class ORDER BY month, uf, class"""
        totals = db.execute(query)
        with (output / "reference-by-month-state-class.csv").open("w", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(field[0] for field in totals.description)
            writer.writerows(totals)
        total, unique_ids, unknown_areas = db.execute(
            "SELECT COUNT(*), COUNT(DISTINCT gid), COUNT(*) - COUNT(reported_area_km2) FROM records"
        ).fetchone()
        classes = dict(db.execute("SELECT class, COUNT(*) FROM records GROUP BY class"))
        years = Counter()
        for metadata in months:
            years[metadata["start"][:4]] += metadata["features"]
        report = {"months": len(months), "features": total, "distinct_provider_ids": unique_ids,
                  "missing_reported_areas": unknown_areas, "classes": classes, "features_by_year": years}
        assert total == sum(years.values())
        (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
