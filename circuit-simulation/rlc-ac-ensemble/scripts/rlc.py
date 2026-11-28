"""Validate independent ngspice AC sweeps against the series-RLC response."""

import argparse
import csv
import gzip
import hashlib
import io
import itertools
import json
import math
import re
import resource
import subprocess
import tempfile
import time
from pathlib import Path

BATCHES = 128
CASES_PER_BATCH = 32
ATOL = 1e-10
RTOL = 1e-6
SWEEP_POINTS = 257
SOLVER_TIME = re.compile(r"^Total analysis time \(seconds\) = (.+)$", re.MULTILINE)


def grid(low, high):
    return [10 ** (low + (high - low) * index / 15) for index in range(16)]


def cases():
    return [(index, *values) for index, values in enumerate(
        itertools.product(grid(0, 3), grid(-6, -1), grid(-9, -4))
    )]


def netlist(r, l, c):
    resonance = 1 / (math.tau * math.sqrt(l * c))
    return f"""Series RLC, output across capacitor
V1 in 0 AC 1
R1 in a {r:.17g}
L1 a out {l:.17g}
C1 out 0 {c:.17g}
.control
set numdgt=17
set wr_singlescale
ac dec 32 1 100meg
wrdata sweep.dat v(out)
ac lin 1 {resonance:.17g} {resonance:.17g}
wrdata resonance.dat v(out)
rusage
quit
.endc
.end
"""


def response(frequency, r, l, c):
    omega = math.tau * frequency
    return 1 / complex(1 - l * c * omega**2, r * c * omega)


def prepare():
    inventory = []
    for index, r, l, c in cases():
        inventory.append({"circuit": index, "batch": index // CASES_PER_BATCH, "R_ohm": r,
                          "L_henry": l, "C_farad": c,
                          "netlist_sha256": hashlib.sha256(netlist(r, l, c).encode()).hexdigest()})
    if len(inventory) != BATCHES * CASES_PER_BATCH:
        raise ValueError("Unexpected circuit inventory")
    Path("manifest.json").write_text(json.dumps(inventory, sort_keys=True) + "\n")


def simulate(binary, folder, circuit):
    index, r, l, c = circuit
    (folder / "fixture.cir").write_text(netlist(r, l, c))
    start = time.monotonic()
    process = subprocess.run([binary, "-b", "-n", "fixture.cir"], cwd=folder,
                             capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(f"ngspice failed for circuit {index}: {process.stderr.strip()}")
    runtime = time.monotonic() - start
    start = time.monotonic()
    metrics = []
    peak = 0.0
    for kind, count in (("sweep", SWEEP_POINTS), ("resonance", 1)):
        path = folder / f"{kind}.dat"
        rows = [tuple(map(float, line.split())) for line in path.read_text().splitlines()]
        path.unlink()
        if len(rows) != count:
            raise ValueError(f"Circuit {index} {kind} returned {len(rows)} samples")
        for frequency, real, imaginary in rows:
            expected = response(frequency, r, l, c)
            error = abs(complex(real, imaginary) - expected)
            ratio = error / (ATOL + RTOL * abs(expected))
            if not math.isfinite(ratio) or ratio > 1:
                raise ValueError(f"Circuit {index} at {frequency} Hz exceeded tolerance: {ratio}")
            peak = max(peak, ratio)
            metrics.append((index, kind, frequency, real, imaginary,
                            expected.real, expected.imag, ratio))
    match = SOLVER_TIME.search(process.stdout)
    if match is None:
        raise ValueError(f"ngspice did not report analysis time for circuit {index}")
    telemetry = {"circuit": index, "ngspice_wall_seconds": runtime,
                 "solver_analysis_seconds": float(match[1]),
                 "parse_validate_seconds": time.monotonic() - start,
                 "max_error_fraction": peak,
                 "solver_resource_lines": [line.strip() for line in process.stdout.splitlines()
                                           if "time" in line.lower()]}
    return metrics, telemetry


def run_batch(binary, batch):
    inventory = cases()[batch * CASES_PER_BATCH:(batch + 1) * CASES_PER_BATCH]
    expected = json.loads(Path("manifest.json").read_text())
    if len(expected) != BATCHES * CASES_PER_BATCH:
        raise ValueError("Prepared manifest does not contain the full circuit grid")
    stem = f"batch-{batch:03d}"
    records = []
    start = time.monotonic()
    with tempfile.TemporaryDirectory(dir=".") as temporary:
        folder = Path(temporary)
        (folder / "startup.cir").write_text("Startup control\nV1 in 0 AC 1\nR1 in 0 1\n.control\nquit\n.endc\n.end\n")
        startup_seconds = []
        for _ in range(3):
            started = time.monotonic()
            subprocess.run([binary, "-b", "-n", "startup.cir"], cwd=folder,
                           capture_output=True, check=True)
            startup_seconds.append(time.monotonic() - started)
        data = folder / f"{stem}.csv.gz"
        with data.open("wb") as output:
            with gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as archive:
                with io.TextIOWrapper(archive, newline="") as stream:
                    writer = csv.writer(stream, lineterminator="\n")
                    writer.writerow(("circuit", "kind", "frequency_hz", "real", "imaginary",
                                     "expected_real", "expected_imaginary", "error_fraction"))
                    for circuit in inventory:
                        index, r, l, c = circuit
                        digest = hashlib.sha256(netlist(r, l, c).encode()).hexdigest()
                        if expected[index]["netlist_sha256"] != digest:
                            raise ValueError(f"Netlist digest mismatch for circuit {index}")
                        metrics, telemetry = simulate(binary, folder, circuit)
                        writer.writerows(metrics)
                        records.append(telemetry)
        report = {"batch": batch, "circuits": records, "elapsed_seconds": time.monotonic() - start,
                  "startup_control_seconds": startup_seconds,
                  "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  "sha256": hashlib.sha256(data.read_bytes()).hexdigest()}
        report_path = folder / f"{stem}.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        data.replace(data.name)
        report_path.replace(report_path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "batch"))
    parser.add_argument("--batch", type=int, choices=range(BATCHES), metavar="INDEX")
    parser.add_argument("--binary", default="ngspice")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.batch is None:
        parser.error("batch mode requires --batch")
    else:
        run_batch(args.binary, args.batch)
