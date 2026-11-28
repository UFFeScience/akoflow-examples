"""Export integer histograms and reduce independently seeded walk batches."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from walks import BATCHES, PARTICLES, SCENARIOS, batch, estimate_checks, sufficient_statistics, validate

FIELDS = ("x","y","count")


def name(scenario, index):
    return f"{scenario}-{index:03d}.csv"


def write_histogram(path, histogram):
    with path.open("w", newline="") as stream:
        writer=csv.writer(stream,lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows((x,y,histogram[x,y]) for x,y in sorted(histogram))


def load_histogram(path, steps):
    with path.open(newline="") as stream:
        reader=csv.DictReader(stream)
        if tuple(reader.fieldnames or ())!=FIELDS:
            raise ValueError(f"Unexpected histogram columns in {path.name}")
        output=Counter()
        for row in reader:
            point=int(row["x"]),int(row["y"])
            if point in output:
                raise ValueError(f"Duplicate endpoint in {path.name}")
            output[point]=int(row["count"])
    validate(output,steps,PARTICLES)
    return output


def reduce(source, output, steps):
    expected={source/name(scenario,index) for scenario in SCENARIOS for index in range(BATCHES)}
    actual={path for scenario in SCENARIOS for path in source.glob(f"{scenario}-[0-9][0-9][0-9].csv")}
    if expected!=actual:
        raise ValueError("Missing or unexpected batch files")
    output.mkdir(parents=True,exist_ok=True)
    report=[]
    with (output/"batch-moments.csv").open("w",newline="") as stream:
        writer=csv.writer(stream,lineterminator="\n")
        writer.writerow(("scenario","batch","count","sum_x","sum_y","sum_xx","sum_yy","sum_xy"))
        for scenario in SCENARIOS:
            batches=[load_histogram(source/name(scenario,index),steps) for index in range(BATCHES)]
            merged=Counter()
            for index,histogram in enumerate(batches):
                writer.writerow((scenario,index,*sufficient_statistics(histogram)))
                merged.update(histogram)
            reverse=Counter()
            for histogram in reversed(batches):
                reverse.update(histogram)
            if merged!=reverse:
                raise ValueError("Reduction order changed integer counts")
            observed,covariance,expected_mean,expected_cov=estimate_checks(merged,scenario,steps)
            write_histogram(output/f"{scenario}-endpoints.csv",merged)
            report.append({"scenario":scenario,"steps":steps,"particles":sum(merged.values()),
                           "observed_mean":observed.tolist(),"expected_mean":expected_mean.tolist(),
                           "observed_covariance":covariance.tolist(),"expected_covariance":expected_cov.tolist()})
    (output/"moment-validation.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps",type=int,choices=(80,320),default=80)
    sub=parser.add_subparsers(dest="command",required=True)
    worker=sub.add_parser("batch")
    worker.add_argument("scenario",choices=tuple(SCENARIOS))
    worker.add_argument("index",type=int,choices=range(BATCHES))
    worker.add_argument("output",type=Path)
    reducer=sub.add_parser("aggregate")
    reducer.add_argument("source",type=Path)
    reducer.add_argument("output",type=Path)
    args=parser.parse_args()
    if args.command=="batch":
        write_histogram(args.output/name(args.scenario,args.index),batch(args.scenario,args.index,args.steps))
    else:
        reduce(args.source,args.output,args.steps)
