#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("logs")
    parser.add_argument("output")
    args = parser.parse_args()
    payload = json.loads(Path(args.logs).read_text())
    handles = sorted(payload["handles"], key=lambda item: item["startedAt"])
    origin = min(item["startedAt"] for item in handles)
    predictions = [item for item in handles if "-predict-" in item["activityId"]]
    boundaries = sorted({value for item in predictions for value in (item["startedAt"], item["finishedAt"])})
    intervals = []
    for start, finish in zip(boundaries, boundaries[1:]):
        active = [item for item in predictions
                  if item["startedAt"] <= start and item["finishedAt"] >= finish]
        if finish > start:
            intervals.append((len(active), finish - start, start, finish, active))
    concurrency, overlap, overlap_start, overlap_finish, overlap_activities = max(intervals)

    figure, axis = plt.subplots(figsize=(11, 7), constrained_layout=True)
    for row, item in enumerate(handles):
        name = item["activityId"].split("equivariance-v1-")[-1]
        start = item["startedAt"] - origin
        prediction = item in predictions
        axis.barh(row, item["finishedAt"] - item["startedAt"], left=start,
                  color="#111111" if prediction else "#aaaaaa", height=0.65)
        axis.text(start + 0.03, row, name, va="center", fontsize=8,
                  color="white" if prediction else "black")
    if overlap > 0:
        axis.axvspan(overlap_start - origin, overlap_finish - origin, color="#d9d9d9", alpha=0.5,
                     label=f"measured {concurrency}-way overlap: {overlap:.3f} s")
    axis.set(xlabel="Seconds since first activity start", ylabel="Measured activity order",
             title=f"Akoflow measured timeline — {payload['run']['id']}")
    axis.set_yticks([])
    axis.grid(axis="x", alpha=0.2)
    if overlap > 0:
        axis.legend(loc="lower right")
    figure.savefig(args.output, dpi=180)

    evidence = {
        "run_id": payload["run"]["id"], "workflow_version_id": payload["run"]["workflowVersionId"],
        "status": payload["run"]["status"], "makespan_seconds": payload["run"]["makespanSeconds"],
        "compute_seconds": payload["run"]["breakdown"]["computeSeconds"],
        "transferred_bytes": payload["run"]["transferredBytes"],
        "prediction_overlap": {"activities": [item["activityId"] for item in overlap_activities],
                               "maximum_concurrency": concurrency,
                               "start_unix": overlap_start, "finish_unix": overlap_finish,
                               "seconds": overlap},
        "speedup_claimed": False,
    }
    Path(args.output).with_suffix(".json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
