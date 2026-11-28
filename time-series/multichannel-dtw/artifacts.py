"""Export auditable alignment paths and aggregate their event errors."""

import argparse
import csv
import math
from pathlib import Path

from alignment import CASES, STRATEGIES, channel_losses, signals, solve
from render import render

FIELDS = ("case", "seed", "shift", "strategy", "channel", "step", "source_index",
          "target_index", "local_cost", "source_event", "target_event")


def write_case(case, length, output):
    seed, shift, strategy = CASES[case]
    a, b, anchors, shifted = signals(seed, shift, length)
    _, paths, _ = solve(a, b, strategy)
    matrices = channel_losses(a, b)
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        for channel, path in enumerate(paths):
            for step, (i, j) in enumerate(path):
                writer.writerow((case, seed, shift, strategy, channel, step, i, j,
                                 matrices[channel][i, j], anchors[channel], shifted[channel]))


def case_metrics(source, case, length):
    seed, shift, strategy = CASES[case]
    a, b, anchors, shifted = signals(seed, shift, length)
    local = channel_losses(a, b)
    channels = ([], [])
    with source.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(f"Incorrect path columns for case {case}")
        for row in reader:
            channel = int(row["channel"])
            if channel not in (0, 1):
                raise ValueError(f"Invalid channel for case {case}")
            key = tuple(int(row[field]) for field in ("case", "seed", "shift"))
            if key != (case, seed, shift) or row["strategy"] != strategy:
                raise ValueError(f"Incorrect case labels in case {case}")
            if (int(row["source_event"]), int(row["target_event"])) != (anchors[channel], shifted[channel]):
                raise ValueError(f"Incorrect event labels in case {case}")
            i, j = int(row["source_index"]), int(row["target_index"])
            if (int(row["step"]) != len(channels[channel]) or not 0 <= i < length or not 0 <= j < length
                    or float(row["local_cost"]) != local[channel][i, j]):
                raise ValueError(f"Invalid path record in case {case}")
            channels[channel].append((i,j))
    for path in channels:
        if not path or path[0] != (0,0) or path[-1] != (length-1, length-1):
            raise ValueError(f"Invalid endpoints in case {case}")
        if any((j-i, y-x) not in ((0,1),(1,0),(1,1))
               for (i,x),(j,y) in zip(path,path[1:])):
            raise ValueError(f"Invalid path step in case {case}")
    if strategy=="common" and channels[0] != channels[1]:
        raise ValueError(f"Expected a shared path in case {case}")
    cost=math.fsum(local[channel][i,j] for channel,path in enumerate(channels) for i,j in path)
    mapped=[tuple(j for i,j in channels[channel] if i==anchors[channel]) for channel in (0,1)]
    error=[min(abs(j-shifted[channel]) for j in positions) for channel,positions in enumerate(mapped)]
    frame_disagreement = len(set(channels[0]) ^ set(channels[1]))
    cells=length**2*(1 if strategy=="common" else 2)
    return (case, seed, shift, strategy, cost, cells, *error, int(frame_disagreement))


def aggregate(source, length, output):
    paths=[source/f"case-{case:03d}.csv" for case in range(len(CASES))]
    if {path.name for path in source.glob("case-*.csv")} != {path.name for path in paths}:
        raise ValueError("Missing or extra case outputs")
    rows=[case_metrics(path,case,length) for case,path in enumerate(paths)]
    for common, independent in zip(rows[::2],rows[1::2],strict=True):
        if common[1:3]!=independent[1:3] or (common[3],independent[3])!=STRATEGIES:
            raise ValueError("Incorrect comparison pairing")
        if independent[4]>common[4] and not math.isclose(independent[4],common[4],abs_tol=1e-12):
            raise ValueError("Independent path cost exceeds the common path cost")
        if common[2]==0 and (common[4]!=0 or independent[4]!=0):
            raise ValueError("Identity control does not have zero cost")
    with output.open("w", newline="") as stream:
        writer=csv.writer(stream, lineterminator="\n")
        writer.writerow(("case","seed","shift","strategy","cost","cells_evaluated",
                         "channel_0_event_error","channel_1_event_error","joint_path_disagreement"))
        writer.writerows(rows)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length", type=int, choices=(96,192), default=96)
    sub=parser.add_subparsers(dest="command",required=True)
    case=sub.add_parser("case")
    case.add_argument("case",type=int,choices=range(len(CASES)))
    case.add_argument("output",type=Path)
    all_cases=sub.add_parser("aggregate")
    all_cases.add_argument("source",type=Path)
    all_cases.add_argument("output",type=Path)
    args=parser.parse_args()
    if args.command=="case":
        write_case(args.case,args.length,args.output)
    else:
        args.output.mkdir(parents=True,exist_ok=True)
        aggregate(args.source,args.length,args.output/"alignment-summary.csv")
        render(args.length,args.output)
