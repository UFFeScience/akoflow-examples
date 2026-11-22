#!/usr/bin/env python3
"""Render a measured Akoflow activity timeline from GET /logs/ JSON."""

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
    simulation = [item for item in handles if "simulate-n" in item["activityId"]]
    overlap_start = max(item["startedAt"] for item in simulation)
    overlap_finish = min(item["finishedAt"] for item in simulation)

    fig, axis = plt.subplots(figsize=(11, 7), constrained_layout=True)
    colors = {"simulate": "#111111", "measure": "#666666", "other": "#aaaaaa"}
    for row, item in enumerate(handles):
        name = item["activityId"].split("-r2-")[-1]
        kind = "simulate" if name.startswith("simulate") else "measure" if name.startswith("measure") else "other"
        start = item["startedAt"] - origin
        axis.barh(row, item["finishedAt"] - item["startedAt"], left=start,
                  color=colors[kind], height=0.65)
        axis.text(start + 0.03, row, name, va="center", ha="left", fontsize=8,
                  color="white" if kind == "simulate" else "black")
    axis.axvspan(overlap_start - origin, overlap_finish - origin, color="#d9d9d9", alpha=0.45,
                 label=f"four-way simulation overlap: {overlap_finish - overlap_start:.3f} s")
    axis.set(xlabel="Seconds since first activity start", ylabel="Measured activity order",
             title=f"Akoflow measured timeline — {payload['run']['id']}")
    axis.set_yticks([]); axis.grid(axis="x", alpha=0.2); axis.legend(loc="lower right")
    fig.savefig(args.output, dpi=180)

    evidence = {
        "run_id": payload["run"]["id"],
        "workflow_version_id": payload["run"]["workflowVersionId"],
        "status": payload["run"]["status"],
        "makespan_seconds": payload["run"]["makespanSeconds"],
        "compute_seconds": payload["run"]["breakdown"]["computeSeconds"],
        "transferred_bytes": payload["run"]["transferredBytes"],
        "simulation_overlap": {
            "activities": [item["activityId"] for item in simulation],
            "start_unix": overlap_start,
            "finish_unix": overlap_finish,
            "seconds": overlap_finish - overlap_start,
        },
        "speedup_claimed": False,
    }
    Path(args.output).with_suffix(".json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
