import argparse
import csv
import hashlib
import json
from pathlib import Path

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

REVISION = "2ee7756575ff6f90981d0308cbcb6a2ab5995bdc"
VALUES = ("0.03", "0.06", "0.10", "0.18", "0.32", "0.56", "1.00", "1.78", "3.16")
HASHES = {
    "0.03": "7cfc3b5be027792100b20cc4c1ab2f2835f983b00f6f86c3833bb52484c5a68e",
    "0.06": "7274a1ee2daf404e392cafac0a7de08668a834d78c5af48ed1c3eb844822be99",
    "0.10": "4a8d39a19bea829b01de8c25a78fa7d089de82f14c676fca3a94365e6e994ebe",
    "0.18": "30a0218124429556c889dfbb94b3f20acee1946d35d74c7ed5179b717f57dc21",
    "0.32": "06cbd36c1dbea84e70906a363d20143b228765ee37850ec65351e247cf7df747",
    "0.56": "d69d6f41c950d69e2a21688c65e303fd5cd415c37ec686df055db7da73a838fe",
    "1.00": "97f5d10132c6f4b100d1c77d94e91fa2acdc4954cc359733087b9ae5fc983838",
    "1.78": "f53524c481e095be20d607dd3f9a2738dd1a2dd8c0a675c0794f000822c79c2b",
    "3.16": "02a7d46a9ac1f36a479d32396a07818e26832015d083dee63845d64b92b39cf3",
}
B1 = 0.01 * 100.0 ** (1.0 / 3.0)
B2 = 0.01 * 100.0 ** (2.0 / 3.0)
EXPECTED = {"0.03": 0.006539901430843709, "0.06": 0.005454962151770215,
            "0.10": 0.003189510695692843, "0.18": 0.0018754790536616994,
            "0.32": 0.00032391607148629653, "0.56": -0.0015361755973030133,
            "1.00": -0.005922510485302568, "1.78": -0.00996198376860069,
            "3.16": -0.00849569362010294}


def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def prepare(root):
    dump(root / "protocol.json", {
        "dataset": "polymathic-ai/turbulent_radiative_layer_2D", "revision": REVISION,
        "license": "CC-BY-4.0", "scope": "one official test trajectory per cooling time",
        "cooling_times": list(VALUES), "object_sha256": HASHES,
        "temperature": "pressure / density", "initial_equilibria": [0.01, 1.0],
        "phase_boundaries": [B1, B2], "late_window": "final 21 of 101 frames",
        "accumulation": "float64", "readme_trajectories": 90,
        "distributed_trajectories": 72, "test_trajectories": 9,
        "limitations": ["single test trajectory per cooling time", "no seed uncertainty",
                        "not the associated paper's 3D scaling experiment"],
    })


def analyze(root, value):
    if value not in VALUES: raise ValueError(value)
    branch = root / "branches" / f"tcool-{value}"
    branch.mkdir(parents=True, exist_ok=True)
    name = f"turbulent_radiative_layer_tcool_{value}.hdf5"
    path = Path("/inputs") / name
    actual = sha256(path)
    if actual != HASHES[value]: raise RuntimeError(f"hash mismatch {actual}")
    with h5py.File(path, "r") as f:
        if int(f.attrs["n_trajectories"]) != 1 or abs(float(f.attrs["tcool"]) - float(value)) > 1e-12:
            raise RuntimeError("identity mismatch")
        rho = f["t0_fields/density"][0].astype(np.float64)
        pressure = f["t0_fields/pressure"][0].astype(np.float64)
        velocity = f["t1_fields/velocity"][0].astype(np.float64)
        times = f["dimensions/time"][:].astype(np.float64)
        x = f["dimensions/x"][:].astype(np.float64); y = f["dimensions/y"][:].astype(np.float64)
        xb = f["boundary_conditions/x_periodic"].attrs["bc_type"]
        yb = f["boundary_conditions/y_open"].attrs["bc_type"]
        if rho.shape != (101, 128, 384) or velocity.shape != (101, 128, 384, 2):
            raise RuntimeError("schema mismatch")
        if not (np.isfinite(rho).all() and np.isfinite(pressure).all() and np.isfinite(velocity).all()):
            raise RuntimeError("non-finite values")
        if rho.min() <= 0 or pressure.min() <= 0: raise RuntimeError("non-positive thermodynamic field")
        temp = pressure / rho; mass = rho.sum(axis=(1, 2), dtype=np.float64)
        cold = (rho * (temp <= B1)).sum(axis=(1, 2), dtype=np.float64) / mass
        intermediate = (rho * ((temp > B1) & (temp < B2))).sum(axis=(1, 2), dtype=np.float64) / mass
        hot = (rho * (temp >= B2)).sum(axis=(1, 2), dtype=np.float64) / mass
        vrms = np.sqrt((rho * np.square(velocity).sum(axis=-1)).sum(axis=(1, 2), dtype=np.float64) / mass)
        if np.max(np.abs(cold + intermediate + hot - 1.0)) > 1e-12: raise RuntimeError("phase closure")
        with (branch / "frames.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle); writer.writerow(["frame", "time", "cold", "intermediate", "hot", "vrms", "mass", "mass_drift"])
            for i in range(101): writer.writerow([i, f"{times[i]:.12g}", f"{cold[i]:.17g}", f"{intermediate[i]:.17g}", f"{hot[i]:.17g}", f"{vrms[i]:.17g}", f"{mass[i]:.17g}", f"{mass[i]/mass[0]-1:.17g}"])
        late = np.arange(101) >= 80
        summary = {"tcool": float(value), "sha256": actual, "frames": 101,
                   "late_start_time": float(times[80]), "cold_initial": float(cold[0]),
                   "cold_final": float(cold[-1]), "cold_delta_late": float(cold[late].mean()-cold[0]),
                   "intermediate_late": float(intermediate[late].mean()), "hot_late": float(hot[late].mean()),
                   "vrms_late": float(vrms[late].mean()), "mass_drift_final": float(mass[-1]/mass[0]-1),
                   "x_range": [float(x[0]), float(x[-1])], "y_range": [float(y[0]), float(y[-1])],
                   "boundaries": [str(xb), str(yb)]}
        dump(branch / "summary.json", summary)


def aggregate(root):
    rows=[]
    for value in VALUES:
        p=root/"branches"/f"tcool-{value}"/"summary.json"
        rows.append(json.loads(p.read_text()))
    dump(root/"aggregate.json", {"rows":rows, "phase_boundaries":[B1,B2],
         "sign_transition":[0.32,0.56], "trajectory_count":9})
    with (root/"aggregate.csv").open("w",newline="",encoding="utf-8") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def render(root):
    data=json.loads((root/"aggregate.json").read_text()); rows=data["rows"]
    x=np.array([r["tcool"] for r in rows]); y=np.array([r["cold_delta_late"] for r in rows])
    fig,ax=plt.subplots(figsize=(8,5)); ax.axhline(0,color="black",lw=1); ax.plot(x,y,"o-",color="#111111")
    ax.set_xscale("log"); ax.set_xlabel("Cooling time"); ax.set_ylabel("Late cold mass-fraction change"); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(root/"cooling-time-trend.png",dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5))
    series=[]
    for value in VALUES:
        a=np.genfromtxt(root/"branches"/f"tcool-{value}"/"frames.csv",delimiter=",",names=True)
        ax.plot(a["time"],a["cold"]-a["cold"][0],label=value); series.append(a)
    ax.set_xlabel("Simulation time"); ax.set_ylabel("Cold mass-fraction change"); ax.legend(title="t_cool",ncol=3); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(root/"cold-phase-evolution.png",dpi=180); plt.close(fig)
    frames=[]
    for end in range(1,102,4):
        fig,ax=plt.subplots(figsize=(8,5)); ax.axhline(0,color="black",lw=1)
        for value,a in zip(VALUES,series): ax.plot(a["time"][:end],a["cold"][:end]-a["cold"][0],label=value)
        ax.set_xlim(0,160); ax.set_ylim(-.011,.008); ax.set_xlabel("Simulation time"); ax.set_ylabel("Cold mass-fraction change"); ax.legend(ncol=3,fontsize=7); fig.tight_layout()
        fig.canvas.draw(); image=np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy(); frames.append(Image.fromarray(image)); plt.close(fig)
    frames[0].save(root/"phase-evolution.gif",save_all=True,append_images=frames[1:],duration=180,loop=0,optimize=True)


def validate(root):
    data=json.loads((root/"aggregate.json").read_text()); errors=[]
    if len(data["rows"]) != 9: errors.append("coverage")
    for value,row in zip(VALUES,data["rows"]):
        if abs(row["cold_delta_late"]-EXPECTED[value]) > 1e-10: errors.append("metric-"+value)
        if row["sha256"] != HASHES[value]: errors.append("hash-"+value)
    if not (data["rows"][4]["cold_delta_late"]>0 and data["rows"][5]["cold_delta_late"]<0): errors.append("transition")
    artifacts={p.name:sha256(p) for p in [root/"aggregate.json",root/"aggregate.csv",root/"cooling-time-trend.png",root/"cold-phase-evolution.png",root/"phase-evolution.gif"]}
    report={"passed":not errors,"errors":errors,"tolerance":1e-10,"artifacts":artifacts,"checks":9*2+2}
    dump(root/"validation.json",report)
    if errors: raise RuntimeError(errors)


def main():
    p=argparse.ArgumentParser(); p.add_argument("stage",choices=["prepare","analyze","aggregate","render","validate"]); p.add_argument("--output",default="."); p.add_argument("--tcool")
    a=p.parse_args(); root=Path(a.output); root.mkdir(parents=True,exist_ok=True)
    {"prepare":lambda:prepare(root),"analyze":lambda:analyze(root,a.tcool),"aggregate":lambda:aggregate(root),"render":lambda:render(root),"validate":lambda:validate(root)}[a.stage]()
if __name__=="__main__": main()
