"""Verify all DETER monthly audits against the frozen independent reference."""

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from math import isclose
from pathlib import Path


def load_reference(path):
    with path.open(newline="") as stream:
        return {(row["month"], row["uf"], row["class"]):
                (int(row["feature_count"]), float(row["reported_area_km2"]))
                for row in csv.DictReader(stream)}


def aggregate(input_folder, metadata, reference):
    inventory = {row["start"][:7]: row for row in metadata["months"]}
    names = {f"audit-{month}.json" for month in inventory}
    if {path.name for path in input_folder.glob("audit-*.json")} != names:
        raise ValueError("Unexpected monthly audit inventory")
    matched = set()
    audits, rows = [], []
    flags = Counter()
    for month, expected in sorted(inventory.items()):
        audit = json.loads((input_folder / f"audit-{month}.json").read_text())
        if (audit["month"], audit["input_sha256"], audit["features"]) != (
                month, expected["sha256"], expected["features"]):
            raise ValueError(f"Manifest mismatch for {month}")
        if sum(group["feature_count"] for group in audit["groups"]) != audit["features"]:
            raise ValueError(f"Report counts do not match the source partition for {month}")
        flags.update(audit["flags"])
        for row in audit["groups"]:
            key = month, row["uf"], row["class"]
            if key in matched or key not in reference:
                raise ValueError(f"Unexpected or repeated result partition {key}")
            count, reported = reference[key]
            if row["feature_count"] != count or not isclose(
                    row["reported_area_km2"], reported, rel_tol=1e-12, abs_tol=1e-8):
                raise ValueError(f"Reference mismatch for {key}")
            matched.add(key)
            rows.append({"month": month, **row})
        audits.append(audit)
    if matched != reference.keys():
        raise ValueError("Missing results for one or more reference groups")
    validation = {"passed": True, "months": len(audits),
                  "features": sum(audit["features"] for audit in audits),
                  "reference_groups": len(matched), "flags": dict(sorted(flags.items()))}
    return audits, rows, validation


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit_folder", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    metadata = json.loads((args.snapshot / "manifest.json").read_text())
    if len(metadata["months"]) != 72:
        raise ValueError("Expected 72 months from January 2019 to December 2024")
    audits, rows, validation = aggregate(args.audit_folder, metadata, load_reference(args.reference))
    args.output.mkdir(parents=True, exist_ok=True)
    table = args.output / "deter-month-state-class.csv"
    write_csv(table, rows)
    months = [{"month": audit["month"], "features": audit["features"], **audit["flags"],
               "spherical_area_km2_valid_shapes": audit["spherical_area_km2_valid_shapes"]}
              for audit in audits]
    keys = sorted(set().union(*(row.keys() for row in months)) - {"month"})
    diagnostics = args.output / "deter-monthly-diagnostics.csv"
    write_csv(diagnostics, [{"month": row["month"], **{key: row.get(key, 0) for key in keys}}
                            for row in months])
    from render import render

    map_path, animation, frame_count = render(audits, args.snapshot, args.output)
    validation["animation_frames"] = frame_count
    validation["sha256"] = {path.name: sha256(path.read_bytes()).hexdigest()
                            for path in (table, diagnostics, map_path, animation)}
    (args.output / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")


if __name__ == "__main__":
    main()
