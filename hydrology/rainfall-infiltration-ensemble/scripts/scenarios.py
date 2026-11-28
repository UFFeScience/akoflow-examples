"""Freeze the 512 rainfall scenarios and generate deterministic soil columns."""

from itertools import product
import json
import random
import sys

RAIN = (4, 8, 12, 16, 24, 36, 60, 90)
CONDUCTIVITY = (4, 8, 16, 32)
MOISTURE_DEFICIT = (0.10, 0.17, 0.24, 0.31)
SEEDS = (17, 47, 73, 101)
SUCTION_MM = 100


def batches():
    for index, (rain, conductivity, deficit, seed) in enumerate(
        product(RAIN, CONDUCTIVITY, MOISTURE_DEFICIT, SEEDS)
    ):
        yield {
            "id": f"batch-{index:03d}", "seed": seed + 1024 * index,
            "rain_mm_h": rain, "conductivity_mm_h": conductivity,
            "moisture_deficit": deficit, "suction_mm": SUCTION_MM,
        }


def columns(batch, count):
    rng = random.Random(batch["seed"])
    for _ in range(count):
        yield (
            batch["rain_mm_h"],
            batch["conductivity_mm_h"] * rng.uniform(0.9, 1.1),
            batch["suction_mm"] * rng.uniform(0.85, 1.15) * batch["moisture_deficit"],
        )


if __name__ == "__main__":
    json.dump({"storm_hours": 4, "sample_interval_minutes": 2, "batches": list(batches())}, sys.stdout)
    print()
