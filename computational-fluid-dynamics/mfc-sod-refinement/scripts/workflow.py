#!/usr/bin/env python3
"""Qualified MFC v4.9.9 Sod refinement workflow stages."""

import argparse
import hashlib
import json
import math
import os
import pathlib
import shutil
import struct
import subprocess

GAMMA = 1.4
FINAL_TIME = 0.1
DISCONTINUITY = 0.5
RESOLUTIONS = (100, 200, 400, 800)
FIELDS = ("density", "velocity", "pressure")
EXPECTED_ORDERS = {"density": 0.927776, "velocity": 0.986335, "pressure": 0.991450}
EXPECTED_ERRORS = {
    100: (0.00332641297392204, 0.007187011028274121, 0.002725182919170022),
    200: (0.0017125745723256304, 0.0039289634156148955, 0.001491920960328745),
    400: (0.0009536509753016517, 0.001957833988217819, 0.0007352216657279762),
    800: (0.00047398891833157783, 0.0009282408469389935, 0.0003491277318294909),
}
GL_X = (-0.9602898564975363, -0.7966664774136267, -0.5255324099163290,
        -0.1834346424956498, 0.1834346424956498, 0.5255324099163290,
        0.7966664774136267, 0.9602898564975363)
GL_W = (0.1012285362903763, 0.2223810344533745, 0.3137066458778873,
        0.3626837833783620, 0.3626837833783620, 0.3137066458778873,
        0.2223810344533745, 0.1012285362903763)


def write_json(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def pressure_function(p, rho, p0):
    sound = math.sqrt(GAMMA * p0 / rho)
    if p > p0:
        aa = 2 / ((GAMMA + 1) * rho)
        bb = (GAMMA - 1) / (GAMMA + 1) * p0
        value = (p - p0) * math.sqrt(aa / (p + bb))
        derivative = math.sqrt(aa / (p + bb)) * (1 - (p - p0) / (2 * (p + bb)))
    else:
        value = 2 * sound / (GAMMA - 1) * ((p / p0) ** ((GAMMA - 1) / (2 * GAMMA)) - 1)
        derivative = (1 / (rho * sound)) * (p / p0) ** (-(GAMMA + 1) / (2 * GAMMA))
    return value, derivative


def star_state():
    pressure = 0.3
    for _ in range(30):
        left, dl = pressure_function(pressure, 1.0, 1.0)
        right, dr = pressure_function(pressure, 0.125, 0.1)
        updated = pressure - (left + right) / (dl + dr)
        if abs(updated - pressure) < 1e-14:
            break
        pressure = max(1e-12, updated)
    left, _ = pressure_function(pressure, 1.0, 1.0)
    right, _ = pressure_function(pressure, 0.125, 0.1)
    return pressure, 0.5 * (right - left)


P_STAR, U_STAR = star_state()


def exact_state(x):
    xi = (x - DISCONTINUITY) / FINAL_TIME
    sound_left = math.sqrt(GAMMA)
    sound_right = math.sqrt(GAMMA * 0.1 / 0.125)
    rho_star_left = P_STAR ** (1 / GAMMA)
    sound_star_left = sound_left * P_STAR ** ((GAMMA - 1) / (2 * GAMMA))
    rho_star_right = 0.125 * ((P_STAR / 0.1 + (GAMMA - 1) / (GAMMA + 1)) /
                              ((GAMMA - 1) / (GAMMA + 1) * P_STAR / 0.1 + 1))
    shock = sound_right * math.sqrt((GAMMA + 1) / (2 * GAMMA) * P_STAR / 0.1 +
                                    (GAMMA - 1) / (2 * GAMMA))
    if xi <= -sound_left:
        return 1.0, 0.0, 1.0
    if xi < U_STAR - sound_star_left:
        velocity = 2 / (GAMMA + 1) * (sound_left + xi)
        sound = 2 / (GAMMA + 1) * (sound_left - (GAMMA - 1) * xi / 2)
        return ((sound / sound_left) ** (2 / (GAMMA - 1)), velocity,
                (sound / sound_left) ** (2 * GAMMA / (GAMMA - 1)))
    if xi <= U_STAR:
        return rho_star_left, U_STAR, P_STAR
    if xi < shock:
        return rho_star_right, U_STAR, P_STAR
    return 0.125, 0.0, 0.1


def cell_average(left, right):
    sound_left = math.sqrt(GAMMA)
    sound_star = sound_left * P_STAR ** ((GAMMA - 1) / (2 * GAMMA))
    sound_right = math.sqrt(GAMMA * 0.1 / 0.125)
    shock = sound_right * math.sqrt((GAMMA + 1) / (2 * GAMMA) * P_STAR / 0.1 +
                                    (GAMMA - 1) / (2 * GAMMA))
    waves = [DISCONTINUITY - sound_left * FINAL_TIME,
             DISCONTINUITY + (U_STAR - sound_star) * FINAL_TIME,
             DISCONTINUITY + U_STAR * FINAL_TIME,
             DISCONTINUITY + shock * FINAL_TIME]
    cuts = [left] + [point for point in waves if left < point < right] + [right]
    totals = [0.0, 0.0, 0.0]
    for lo, hi in zip(cuts, cuts[1:]):
        middle, half = (lo + hi) / 2, (hi - lo) / 2
        for coordinate, weight in zip(GL_X, GL_W):
            values = exact_state(middle + half * coordinate)
            for index in range(3):
                totals[index] += half * weight * values[index]
    return tuple(value / (right - left) for value in totals)


def case_definition(n):
    steps = int(2.5 * n)
    return {
        "run_time_info": "T", "x_domain%beg": 0.0, "x_domain%end": 1.0,
        "m": n - 1, "n": 0, "p": 0, "dt": FINAL_TIME / steps,
        "t_step_start": 0, "t_step_stop": steps,
        "t_step_save": max(1, math.ceil(steps / 10)), "num_patches": 2,
        "model_eqns": 2, "alt_soundspeed": "F", "num_fluids": 1,
        "mpp_lim": "F", "mixture_err": "F", "time_stepper": 3,
        "weno_order": 5, "weno_eps": 1e-16, "weno_Re_flux": "F",
        "weno_avg": "F", "mapped_weno": "T", "null_weights": "F",
        "mp_weno": "F", "riemann_solver": 2, "wave_speeds": 1,
        "avg_state": 2, "bc_x%beg": -3, "bc_x%end": -3, "format": 1,
        "precision": 2, "prim_vars_wrt": "T", "parallel_io": "T",
        "patch_icpp(1)%geometry": 1, "patch_icpp(1)%x_centroid": 0.25,
        "patch_icpp(1)%length_x": 0.5, "patch_icpp(1)%vel(1)": 0.0,
        "patch_icpp(1)%pres": 1.0, "patch_icpp(1)%alpha_rho(1)": 1.0,
        "patch_icpp(1)%alpha(1)": 1.0, "patch_icpp(2)%geometry": 1,
        "patch_icpp(2)%x_centroid": 0.75, "patch_icpp(2)%length_x": 0.5,
        "patch_icpp(2)%vel(1)": 0.0, "patch_icpp(2)%pres": 0.1,
        "patch_icpp(2)%alpha_rho(1)": 0.125, "patch_icpp(2)%alpha(1)": 1.0,
        "fluid_pp(1)%gamma": 2.5, "fluid_pp(1)%pi_inf": 0.0,
    }


def prepare(out):
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "scenario.json", {
        "mfc_revision": "06f4418d675016d11df14a05de8b1c32e878de92",
        "mfc_archive_sha256": "a6c239a94875294ecd6a8395aee9cb36e3dc6a31ffb99d0551de890e121da118",
        "reference_revision": "06cd0b8822c52c86d0e9c91e2d214d7e7527c492",
        "reference_archive_sha256": "e0ec32bdc83d5f114af345f5949b1d2bd4f1b78a4fc290d441db5afaa5bd87e0",
        "gamma": GAMMA, "final_time": FINAL_TIME, "resolutions": RESOLUTIONS,
        "timestep_rule": "dt=0.04/N", "reference": "exact cell averages; piecewise 8-point Gauss-Legendre",
        "star_state": {"pressure": P_STAR, "velocity": U_STAR},
    })
    for license_file in pathlib.Path("/licenses").glob("*.txt"):
        shutil.copy2(license_file, out / license_file.name)
    shutil.copy2("/opt/dpkg-manifest.txt", out / "dpkg-manifest.txt")
    shutil.copy2("/opt/python-manifest.txt", out / "python-manifest.txt")


def simulate(out, n):
    if n not in RESOLUTIONS:
        raise SystemExit(f"unsupported resolution {n}")
    case_dir = out / f"case-{n}"
    case_dir.mkdir(parents=True, exist_ok=True)
    case_path = case_dir / "case.py"
    case_path.write_text("#!/usr/bin/env python3\nimport json\nprint(json.dumps(" + repr(case_definition(n)) + "))\n")
    environment = dict(os.environ)
    environment.update({"OMPI_ALLOW_RUN_AS_ROOT": "1", "OMPI_ALLOW_RUN_AS_ROOT_CONFIRM": "1"})
    command = ["/opt/mfc/mfc.sh", "run", str(case_path), "-t", "pre_process", "simulation",
               "post_process", "--no-build", "-j", "1"]
    completed = subprocess.run(command, cwd="/opt/mfc", env=environment, check=False,
                               text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (case_dir / "mfc-run.log").write_text(completed.stdout)
    if completed.returncode:
        raise SystemExit(f"MFC N={n} failed with {completed.returncode}")


def read_restart(path, n):
    raw = path.read_bytes()
    if len(raw) != 4 * n * 8:
        raise ValueError(f"unexpected restart size: {path} {len(raw)}")
    values = struct.unpack("<" + "d" * (4 * n), raw)
    density = values[:n]
    momentum = values[n:2 * n]
    energy = values[2 * n:3 * n]
    velocity = [momentum[i] / density[i] for i in range(n)]
    pressure = [(GAMMA - 1) * (energy[i] - 0.5 * momentum[i] * velocity[i]) for i in range(n)]
    return density, velocity, pressure, energy


def measure(root, out, n):
    case_dir = root / f"case-{n}"
    steps = int(2.5 * n)
    initial_path = case_dir / "restart_data" / "lustre_0.dat"
    final_path = case_dir / "restart_data" / f"lustre_{steps}.dat"
    initial_density, _, _, initial_energy = read_restart(initial_path, n)
    density, velocity, pressure, energy = read_restart(final_path, n)
    width = 1 / n
    reference = [cell_average(i * width, (i + 1) * width) for i in range(n)]
    errors = {field: sum(abs(values[i] - reference[i][j]) for i in range(n)) * width
              for j, (field, values) in enumerate(zip(FIELDS, (density, velocity, pressure)))}
    record = {
        "n": n, "steps": steps, "dt": FINAL_TIME / steps, "errors": errors,
        "mass_initial": sum(initial_density) * width, "mass_final": sum(density) * width,
        "mass_abs_drift": abs(sum(density) * width - sum(initial_density) * width),
        "energy_initial": sum(initial_energy) * width, "energy_final": sum(energy) * width,
        "energy_abs_drift": abs(sum(energy) * width - sum(initial_energy) * width),
        "rho_min": min(density), "pressure_min": min(pressure),
        "final_sha256": digest(final_path),
        "silo_files": len(list((case_dir / "silo_hdf5").rglob("*.silo"))),
    }
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / f"metrics-{n}.json", record)


def aggregate(root, out):
    import matplotlib.pyplot as plt

    records = [json.loads((root / f"metrics-{n}.json").read_text()) for n in RESOLUTIONS]
    ratios, orders = {}, {}
    for field in FIELDS:
        values = [record["errors"][field] for record in records]
        ratios[field] = [values[i + 1] / values[i] for i in range(3)]
        x_values, y_values = [math.log(n) for n in RESOLUTIONS], [math.log(value) for value in values]
        mean_x, mean_y = sum(x_values) / 4, sum(y_values) / 4
        orders[field] = -sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values)) / sum((x - mean_x) ** 2 for x in x_values)
    summary = {"reference": {"p_star": P_STAR, "u_star": U_STAR}, "records": records,
               "fine_over_coarse_ratios": ratios, "fitted_orders": orders}
    write_json(out / "metrics.json", summary)
    colors = {"density": "#111111", "velocity": "#666666", "pressure": "#aaaaaa"}
    fig, axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
    for field in FIELDS:
        axis.loglog(RESOLUTIONS, [r["errors"][field] for r in records], "o-", color=colors[field], label=field)
    axis.set(xlabel="Finite-volume cells", ylabel="L1 error", title="MFC Sod shock-tube refinement")
    axis.grid(True, which="both", alpha=0.2); axis.legend()
    fig.savefig(out / "convergence.png", dpi=180); plt.close(fig)
    n = 800; steps = int(2.5 * n)
    density, velocity, pressure, _ = read_restart(root / f"case-{n}" / "restart_data" / f"lustre_{steps}.dat", n)
    x = [(i + 0.5) / n for i in range(n)]; reference = [cell_average(i / n, (i + 1) / n) for i in range(n)]
    fig, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=True, constrained_layout=True)
    for index, (field, values) in enumerate(zip(FIELDS, (density, velocity, pressure))):
        axes[index].plot(x, [r[index] for r in reference], color="#999999", lw=2, label="exact cell average")
        axes[index].plot(x, values, color="#111111", lw=1, label="MFC N=800")
        axes[index].set_ylabel(field); axes[index].legend(fontsize=8)
    axes[-1].set_xlabel("x"); axes[0].set_title("Sod solution at T=0.1")
    fig.savefig(out / "scientific-result.png", dpi=180); plt.close(fig)


def animate(root, out):
    import matplotlib.pyplot as plt
    from PIL import Image

    n, steps = 800, 2000
    frames = []
    for step in range(0, steps + 1, 200):
        density, _, pressure, _ = read_restart(root / f"case-{n}" / "restart_data" / f"lustre_{step}.dat", n)
        x = [(i + 0.5) / n for i in range(n)]
        fig, axes = plt.subplots(2, 1, figsize=(8, 5), sharex=True, constrained_layout=True)
        axes[0].plot(x, density, color="black"); axes[0].set(ylabel="Density", ylim=(0.05, 1.05))
        axes[1].plot(x, pressure, color="#666666"); axes[1].set(xlabel="x", ylabel="Pressure", ylim=(0.05, 1.05))
        axes[0].set_title(f"MFC Sod evolution: t={step * 0.00005:.3f}")
        fig.canvas.draw(); frames.append(Image.fromarray(__import__("numpy").asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()))
        plt.close(fig)
    frames[0].save(out / "sod-evolution.gif", save_all=True, append_images=frames[1:], duration=140, loop=0)


def validate(root, out):
    metrics = json.loads((root / "metrics.json").read_text())
    records = metrics["records"]
    checks = {
        "all_resolutions": [r["n"] for r in records] == list(RESOLUTIONS),
        "positive_state": all(r["rho_min"] > 0 and r["pressure_min"] > 0 for r in records),
        "conservation": all(r["mass_abs_drift"] <= 1e-12 and r["energy_abs_drift"] <= 1e-12 for r in records),
        "monotone_refinement": all(value < 1 for field in FIELDS for value in metrics["fine_over_coarse_ratios"][field]),
        "order_tolerance": all(abs(metrics["fitted_orders"][field] - EXPECTED_ORDERS[field]) <= 0.15 for field in FIELDS),
        "metric_tolerance": all(abs(record["errors"][field] - EXPECTED_ERRORS[record["n"]][index]) <= 1e-12 for record in records for index, field in enumerate(FIELDS)),
        "postprocessing": all(r["silo_files"] == 22 for r in records),
        "figures": (root / "convergence.png").is_file() and (root / "scientific-result.png").is_file(),
        "animation": (root / "sod-evolution.gif").is_file(),
    }
    report = {"status": "pass" if all(checks.values()) else "fail", "checks": checks,
              "tolerances": {"metrics_absolute": 1e-12, "conservation_absolute": 1e-12, "fitted_order_absolute": 0.15},
              "metrics": metrics}
    write_json(out / "validation.json", report)
    artifacts = [{"name": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": digest(path)}
                 for path in sorted(root.rglob("*")) if path.is_file() and "case-" not in str(path.relative_to(root))]
    write_json(out / "manifest.json", {"publication_key": "community-explorer-issue-5-mfc-sod-refinement",
                                        "validation": report["status"], "artifacts": artifacts})
    if report["status"] != "pass":
        raise SystemExit("validation failed: " + json.dumps(checks, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("prepare", "simulate", "measure", "aggregate", "animate", "validate"))
    parser.add_argument("--input", default="."); parser.add_argument("--output", default=".")
    parser.add_argument("--resolution", type=int)
    args = parser.parse_args(); root, out = pathlib.Path(args.input), pathlib.Path(args.output)
    if args.stage == "prepare": prepare(out)
    elif args.stage == "simulate": simulate(out, args.resolution)
    elif args.stage == "measure": measure(root, out, args.resolution)
    elif args.stage == "aggregate": aggregate(root, out)
    elif args.stage == "animate": animate(root, out)
    elif args.stage == "validate": validate(root, out)


if __name__ == "__main__":
    main()
