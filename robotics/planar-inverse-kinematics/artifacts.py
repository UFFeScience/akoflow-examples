"""Export inverse-kinematics solutions and compare trajectory policies."""

import argparse
import csv
from itertools import product
from math import dist, fsum
from pathlib import Path

from kinematics import FRAMES, TOLERANCE, forward, inverse, select_path, step_cost, targets

FIELDS = ("frame", "target_x", "target_y", "candidate", "shoulder", "elbow", "position_error")


def write_frame(index, point, output):
    path = output / f"frame-{index:03d}.csv"
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        solutions = inverse(*point)
        if solutions:
            for branch, angles in enumerate(solutions):
                writer.writerow((index, *point, branch, *angles, dist(forward(angles), point)))
        else:
            writer.writerow((index, *point, "unreachable", "", "", ""))


def read_frame(path, index, point):
    with path.open(newline="") as stream:
        source = csv.DictReader(stream)
        rows = list(source)
        if tuple(source.fieldnames or ()) != FIELDS:
            raise ValueError(f"Unexpected frame schema in {path.name}")
    if not rows or any(int(row["frame"]) != index or
                       (float(row["target_x"]), float(row["target_y"])) != point for row in rows):
        raise ValueError(f"Unexpected frame or target in {path.name}")
    expected = inverse(*point)
    if not expected:
        if len(rows) != 1 or rows[0]["candidate"] != "unreachable" or any(
                rows[0][key] for key in ("shoulder", "elbow", "position_error")):
            raise ValueError(f"Missing unreachable control in {path.name}")
        return ()
    if len(rows) != len(expected):
        raise ValueError(f"Unexpected number of branches in {path.name}")
    values = []
    for branch, (row, angles) in enumerate(zip(rows, expected, strict=True)):
        actual = float(row["shoulder"]), float(row["elbow"])
        error = dist(forward(actual), point)
        if int(row["candidate"]) != branch or step_cost(actual, angles) > TOLERANCE**2 or (
                error > TOLERANCE or abs(error-float(row["position_error"])) > TOLERANCE):
            raise ValueError(f"Invalid solution in {path.name}")
        values.append(actual)
    return tuple(values)


def total_cost(poses):
    return fsum(step_cost(a,b) for a,b in zip(poses,poses[1:]) if a is not None and b is not None)


def aggregate(source, output, trajectory):
    partition = list(targets(trajectory))
    names = [source / f"frame-{index:03d}.csv" for index in range(FRAMES)]
    if set(source.glob("frame-*.csv")) != set(names):
        raise ValueError("Missing or unexpected frame files")
    candidates = [read_frame(path,index,point) for index,(path,point) in enumerate(zip(names,partition,strict=True))]
    independent = [min(options,key=lambda angles: (step_cost((0,0),angles), angles)) if options else None
                   for options in candidates]
    continuous = select_path(candidates)
    if total_cost(continuous) > total_cost(independent)+TOLERANCE:
        raise ValueError("Continuity optimization increased the total angular change")
    for start in (0,54,96,210,249):
        segment = candidates[start:start+7]
        optimal = min(total_cost(sequence) for sequence in product(*segment))
        if abs(total_cost(select_path(segment))-optimal) > TOLERANCE:
            raise ValueError("Dynamic programming disagrees with exhaustive search")
    output.mkdir(parents=True, exist_ok=True)
    with (output/"trajectory.csv").open("w",newline="") as stream:
        writer = csv.writer(stream,lineterminator="\n")
        writer.writerow(("frame","target_x","target_y","reachable","independent_shoulder",
                         "independent_elbow","continuous_shoulder","continuous_elbow"))
        for index,(point,a,b) in enumerate(zip(partition,independent,continuous,strict=True)):
            writer.writerow((index,*point,bool(a),*(a or ("","")),*(b or ("",""))))
    return independent, continuous


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectory",type=int,default=0)
    commands=parser.add_subparsers(dest="command",required=True)
    frame=commands.add_parser("frame")
    frame.add_argument("index",type=int,choices=range(FRAMES))
    frame.add_argument("output",type=Path)
    reducer=commands.add_parser("aggregate")
    reducer.add_argument("source",type=Path)
    reducer.add_argument("output",type=Path)
    args=parser.parse_args()
    if args.command=="frame":
        write_frame(args.index,list(targets(args.trajectory))[args.index],args.output)
    else:
        aggregate(args.source,args.output,args.trajectory)
