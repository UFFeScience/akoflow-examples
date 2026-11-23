#!/usr/bin/env python3
import argparse, hashlib, json, struct, zlib
from pathlib import Path

def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def branch_rows(run):
    return sorted(
        ({"activity": a["activityId"].rsplit("spectrum-", 1)[1], "resource": a["plannedResourceId"],
          "started_at": a["startedAt"], "finished_at": a["finishedAt"], "runtime_seconds": a["runtimeSeconds"]}
         for a in run["activities"] if "spectrum-" in a["activityId"]),
        key=lambda x: x["started_at"])

def overlaps(rows):
    result = []
    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            seconds = max(0.0, min(left["finished_at"], right["finished_at"]) - max(left["started_at"], right["started_at"]))
            if seconds:
                result.append({"left": left["activity"], "right": right["activity"], "seconds": seconds})
    return result

def timeline_png(path, parallel, serial):
    width, height = 1000, 520
    pixels = [[255] * (width * 3) for _ in range(height)]
    colors = [(31, 119, 180), (44, 160, 44), (255, 127, 14), (214, 39, 40)]
    def rect(x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(height, y1)):
            for x in range(max(0, x0), min(width, x1)):
                pixels[y][3*x:3*x+3] = color
    def axis(y): rect(70, y, 950, y + 2, (30, 30, 30))
    for section, rows, base_y in (("parallel", parallel, 70), ("one-slot", serial, 300)):
        origin = min(r["started_at"] for r in rows)
        for index, row in enumerate(rows):
            x0 = 70 + round((row["started_at"] - origin) / 100 * 880)
            x1 = 70 + round((row["finished_at"] - origin) / 100 * 880)
            rect(x0, base_y + index * 42, max(x0 + 3, x1), base_y + index * 42 + 24, colors[index])
        axis(base_y + 4 * 42 + 12)
    raw = b''.join(b'\0' + bytes(row) for row in pixels)
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("parallel")
    parser.add_argument("one_slot")
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--clean")
    parser.add_argument("--clean-image-digest")
    args = parser.parse_args()
    parallel_doc = json.loads(Path(args.parallel).read_text())
    serial_doc = json.loads(Path(args.one_slot).read_text())
    parallel, serial = branch_rows(parallel_doc), branch_rows(serial_doc)
    timeline_png(args.timeline, parallel, serial)
    parallel_checksums = sorted((x["relativePath"], x["checksum"]) for x in parallel_doc["dataObjects"])
    serial_checksums = sorted((x["relativePath"], x["checksum"]) for x in serial_doc["dataObjects"])
    evidence = {
        "workflow_version": "community-planck-blackbody-v4",
        "parallel_run_id": parallel_doc["run"]["id"],
        "one_slot_run_id": serial_doc["run"]["id"],
        "parallel_status": parallel_doc["run"]["status"],
        "one_slot_status": serial_doc["run"]["status"],
        "parallel_makespan_seconds": parallel_doc["run"]["makespanSeconds"],
        "one_slot_makespan_seconds": serial_doc["run"]["makespanSeconds"],
        "parallel_branches": parallel,
        "one_slot_branches": serial,
        "measured_overlaps": overlaps(parallel),
        "outputs_byte_identical": parallel_checksums == serial_checksums,
        "image_digest": args.image_digest,
        "portable_build_ref": "recipe-build-1a91e496195bfe2098db527452c50c9984c119a79003d2963629ff43d2e4363c",
        "context_digest": "sha256:05e48f00d0f48e73d797a6bb8a99e306dd45dddf656efde42d2c6c5ed61bcef5",
        "recipe_digest": "sha256:7219c30ff8bbac2ae3ead8687e6967ffc819311ca964687515e8bf65eac4be67",
        "timeline_sha256": "sha256:" + hashlib.sha256(Path(args.timeline).read_bytes()).hexdigest(),
        "performance_claim": "No end-to-end speedup claim: the shared host was contended and the parallel run makespan exceeded the one-slot run. Only measured branch overlap is claimed."
    }
    if args.clean:
        clean_doc = json.loads(Path(args.clean).read_text())
        clean_checksums = sorted((x["relativePath"], x["checksum"]) for x in clean_doc["dataObjects"])
        evidence["clean_machine_verification"] = {
            "run_id": clean_doc["run"]["id"],
            "status": clean_doc["run"]["status"],
            "makespan_seconds": clean_doc["run"]["makespanSeconds"],
            "activity_count": clean_doc["run"]["activityCount"],
            "outputs_byte_identical": clean_checksums == parallel_checksums,
            "preflight_observation": "Build required for every activity from an unmaterialized portable-YAML import.",
            "reconstructed_image_digest": args.clean_image_digest,
            "runtime": "fresh isolated AkôFlow daemon, BuildKit, and Docker-in-Docker; no Hub credentials or host Docker socket",
        }
    write_json(args.evidence, evidence)

if __name__ == "__main__":
    main()
