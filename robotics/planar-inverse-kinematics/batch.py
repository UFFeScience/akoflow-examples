"""Run several synthetic trajectories through the same frame partition."""

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from artifacts import aggregate, total_cost, write_frame
from kinematics import FRAMES, targets


def frame_name(trajectory, frame):
    return f"trajectory-{trajectory:02d}-frame-{frame:03d}.csv"


def batch_frame(index, count, output):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output) as temporary:
        work=Path(temporary)
        for trajectory in range(count):
            write_frame(index,list(targets(trajectory))[index],work)
            (work/f"frame-{index:03d}.csv").replace(output/frame_name(trajectory,index))


def batch_reduce(source, count, output):
    expected={source/frame_name(trajectory,frame)
              for trajectory in range(count) for frame in range(FRAMES)}
    if set(source.glob("trajectory-*-frame-*.csv"))!=expected:
        raise ValueError("Missing or unexpected trajectory frames")
    output.mkdir(parents=True, exist_ok=True)
    report=[]
    for trajectory in range(count):
        with ExitStack() as stack:
            inputs=Path(stack.enter_context(TemporaryDirectory()))
            result=Path(stack.enter_context(TemporaryDirectory(dir=output)))
            for frame in range(FRAMES):
                (inputs/f"frame-{frame:03d}.csv").symlink_to(
                    (source/frame_name(trajectory,frame)).resolve())
            independent,continuous=aggregate(inputs,result,trajectory)
            (result/"trajectory.csv").replace(output/f"trajectory-{trajectory:02d}.csv")
            report.append({"trajectory":trajectory,"frames":len(continuous),
                           "unreachable_frames":sum(value is None for value in continuous),
                           "independent_cost":total_cost(independent),
                           "continuous_cost":total_cost(continuous)})
    (output/"batch-summary.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectories",type=int,choices=(2,4),default=4)
    commands=parser.add_subparsers(dest="command",required=True)
    frame=commands.add_parser("frame")
    frame.add_argument("index",type=int,choices=range(FRAMES))
    frame.add_argument("output",type=Path)
    reducer=commands.add_parser("aggregate")
    reducer.add_argument("source",type=Path)
    reducer.add_argument("output",type=Path)
    args=parser.parse_args()
    if args.command=="frame":
        batch_frame(args.index,args.trajectories,args.output)
    else:
        batch_reduce(args.source,args.trajectories,args.output)
