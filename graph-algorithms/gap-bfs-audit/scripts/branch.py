"""Run GAP BFS and reconstruct its per-level logical adjacency checks."""

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

TRACE = re.compile(r"^\s+(td|bu)\s+(\d+)\s+([.0-9]+)$")


def compare_trace(graph, distance, modes):
    """Count probes in the same sorted CSR order as the GAP implementation."""
    layers = [[] for _ in range(max(distance) + 1)]
    for vertex, level in enumerate(distance):
        if level >= 0:
            layers[level].append(vertex)
    if len(modes) != len(layers):
        raise ValueError("Trace and oracle depth disagree")
    rows = []
    for depth, ((mode, observed), frontier) in enumerate(zip(modes, layers)):
        expected = len(layers[depth + 1]) if depth + 1 < len(layers) else 0
        if observed != expected:
            raise ValueError(f"Unexpected frontier at depth {depth}")
        top_down = sum(len(graph[vertex]) for vertex in frontier)
        checks = top_down
        if mode == "bu":
            checks = 0
            for vertex, level in enumerate(distance):
                if 0 <= level <= depth:
                    continue
                for neighbor in graph[vertex]:
                    checks += 1
                    if distance[neighbor] == depth:
                        break
        rows.append({"depth": depth, "frontier": len(frontier), "next_frontier": observed,
                     "mode": mode, "gap_checks": checks, "top_down_checks": top_down})
    return rows


def read_result(folder, output):
    edge_file = folder / "graph-edges.txt"
    edge_bytes = edge_file.read_bytes()
    with edge_file.open() as stream:
        vertices, edges = map(int, stream.readline().split())
        graph = [[] for _ in range(vertices)]
        edge_count = 0
        for line in stream:
            left, right = map(int, line.split())
            graph[left].append(right)
            graph[right].append(left)
            edge_count += 1
    if edge_count != edges:
        raise ValueError("Graph edge count differs from the GAP record")
    for neighbors in graph:
        neighbors.sort()

    graph_time = None
    sources = {}
    for line in output.splitlines():
        if line.startswith("audit graph "):
            graph_time = float(line.split()[-1])
        elif line.startswith("audit source "):
            _, _, source, direction_time, top_down_time = line.split()
            sources[int(source)] = {"source": int(source), "gap_seconds": float(direction_time),
                                    "top_down_seconds": float(top_down_time), "modes": []}
            active = sources[int(source)]
        elif parsed := TRACE.fullmatch(line):
            active["modes"].append((parsed[1], int(parsed[2])))
    if graph_time is None or len(sources) != 3:
        raise ValueError("Incomplete GAP trace")
    for source, result in sources.items():
        content = (folder / f"distances-{source}.txt").read_bytes()
        distances = list(map(int, content.splitlines()))
        if len(distances) != vertices or distances[source] != 0:
            raise ValueError("Invalid independent distance certificate")
        result["reached"] = sum(level >= 0 for level in distances)
        result["distance_sha256"] = hashlib.sha256(content).hexdigest()
        result["levels"] = compare_trace(graph, distances, result.pop("modes"))
    return {"vertices": vertices, "edges": edges, "isolated": sum(not row for row in graph),
            "graph_sha256": hashlib.sha256(edge_bytes).hexdigest(), "graph_seconds": graph_time,
            "sources": list(sources.values())}


def run_case(binary, args, folder):
    trace = subprocess.check_output([binary, *args, "-s"], cwd=folder, text=True)
    return read_result(folder, trace)


def identity(case):
    return case["graph_sha256"], [source["distance_sha256"] for source in case["sources"]]


def run(binary, family):
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        fixture = folder / "control.el"
        fixture.write_text("0 1\n0 2\n1 3\n2 3\n4 5\n")
        run_case(binary, ["-f", str(fixture)], folder)
        control = (folder / "distances-0.txt").read_text().split()
        if list(map(int, control)) != [0, 1, 1, 2, -1, -1]:
            raise ValueError("Disconnected diamond fixture disagrees with expected distances")
        cases = []
        for scale in (14, 16):
            args = ["-g" if family == "kronecker" else "-u", str(scale), "-k", "16"]
            first = run_case(binary, args, folder)
            repeat = run_case(binary, args, folder)
            if identity(first) != identity(repeat):
                raise ValueError(f"Graph or distance certificate changed at scale {scale}")
            cases.append({"scale": scale, **first})
    return {"family": family, "verified": True, "control": list(map(int, control)), "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=("kronecker", "uniform"))
    parser.add_argument("--binary", default="/app/bfs-audit")
    args = parser.parse_args()
    report = run(args.binary, args.family)
    Path(f"{args.family}.json").write_text(json.dumps(report, indent=2) + "\n")
