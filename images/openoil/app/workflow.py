"""Real OpenOil ensemble activities adapted from the user-provided notebook."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import resource
import shutil
import sys
import time

import numpy as np
import xarray as xr


def dump(name, value):
    Path(name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load(name):
    return json.loads(Path(name).read_text())


def fill(a):
    index = np.where(np.isfinite(a), np.arange(a.shape[1]), 0)
    np.maximum.accumulate(index, axis=1, out=index)
    return np.take_along_axis(a, index, axis=1)


def prepare(args):
    scenario = dict(inicio="2026-11-20T06:00:00", lon=-42.90, lat=-23.25,
                    raio_m=1500, horas_vazamento=min(16, args.hours / 2),
                    m3_por_hora=250, oleo="GENERIC MEDIUM CRUDE",
                    horas_simuladas=args.hours, passo_s=900,
                    temperatura_agua=30.0, particulas=args.particles,
                    arquivo_correntes=None, arquivo_vento=None)
    rng = random.Random(42)
    members = []
    for i in range(args.members):
        if rng.random() < 0.5:
            regime, speed, direction = "frente fria", rng.gauss(9, 2), rng.gauss(190, 25)
        else:
            regime, speed, direction = "nordeste", rng.gauss(7, 2), rng.gauss(50, 20)
        speed = max(speed, 1)
        current, towards = max(rng.gauss(.20, .07), 0), rng.gauss(240, 20)
        r = math.radians
        members.append(dict(scenario, membro=i, seed=42 + i, regime=regime,
                            saida=f"membro_{i:03d}", vento_vel=speed, vento_de=direction % 360,
                            vento_u=-speed * math.sin(r(direction)), vento_v=-speed * math.cos(r(direction)),
                            corrente_u=current * math.sin(r(towards)), corrente_v=current * math.cos(r(towards))))
    dump("parameters.json", members)
    dump("scenario.json", dict(scenario, members=args.members, parameter_seed=42,
                               synthetic_forcings=True, total_volume_m3=scenario["horas_vazamento"] * 250,
                               opendrift_version=importlib.metadata.version("opendrift")))


def simulate(index):
    from datetime import datetime, timedelta
    from opendrift.models.openoil import OpenOil
    p = load("parameters.json")[index]
    o = OpenOil(loglevel=50, seed=p["seed"])
    for name, value in {"x_wind": p["vento_u"], "y_wind": p["vento_v"],
                        "x_sea_water_velocity": p["corrente_u"], "y_sea_water_velocity": p["corrente_v"],
                        "sea_water_temperature": p["temperatura_agua"]}.items():
        o.set_config("environment:constant:" + name, value)
    for process in ["evaporation", "emulsification", "dispersion"]:
        o.set_config("processes:" + process, True)
    o.set_config("drift:vertical_mixing", True)
    o.set_config("drift:wind_uncertainty", 1.0)
    o.set_config("drift:current_uncertainty", .05)
    o.set_config("general:coastline_action", "stranding")
    start = datetime.fromisoformat(p["inicio"])
    o.seed_elements(lon=p["lon"], lat=p["lat"], radius=p["raio_m"], number=p["particulas"],
                    time=[start, start + timedelta(hours=p["horas_vazamento"])], z=0,
                    m3_per_hour=p["m3_por_hora"], oil_type=p["oleo"])
    o.run(duration=timedelta(hours=p["horas_simuladas"]), time_step=p["passo_s"],
          time_step_output=3600, outfile=p["saida"] + ".nc",
          export_variables=["lon", "lat", "z", "status", "mass_oil", "mass_evaporated", "mass_dispersed", "water_fraction"])
    with xr.open_dataset(p["saida"] + ".nc") as ds:
        assert ds.sizes["trajectory"] == p["particulas"]
        assert np.isfinite(ds.lon.values).any()
        validate_horizon(ds, p)



def validate_horizon(ds, p):
    hours = ((ds.time.values - np.datetime64(p["inicio"])) / np.timedelta64(1, "h")).astype(float)
    assert len(hours) >= 2 and hours[0] == 0 and np.allclose(np.diff(hours), 1), "Invalid hourly time axis"
    if hours[-1] < p["horas_simuladas"] - 1:
        meanings = ds.status.attrs["flag_meanings"].split()
        values = ds.status.attrs.get("flag_values", list(range(len(meanings))))
        assert "stranded" in meanings and hours[-1] >= p["horas_vazamento"], "Unexpected premature termination"
        stranded = values[meanings.index("stranded")]
        assert np.all(fill(ds.status.transpose("trajectory", "time").values)[:, -1] == stranded), "Early termination with active or missing particles"
    assert hours[-1] <= p["horas_simuladas"], "Time axis exceeds requested horizon"
    return hours


def member_data(p):
    with xr.open_dataset(p["saida"] + ".nc") as ds:
        validate_horizon(ds, p)
        assert ds.sizes["trajectory"] == p["particulas"]
        a = {k: ds[k].transpose("trajectory", "time").values.copy()
             for k in ["lon", "lat", "status", "mass_oil", "mass_evaporated", "mass_dispersed"]}
        meanings = ds.status.attrs["flag_meanings"].split()
        values = ds.status.attrs.get("flag_values", list(range(len(meanings))))
        stranded = int(values[meanings.index("stranded")]) if "stranded" in meanings else None
        coast = np.zeros_like(a["status"], dtype=bool) if stranded is None else fill(a["status"]) == stranded
        hours = ((ds.time.values - np.datetime64(load("scenario.json")["inicio"])) / np.timedelta64(1, "h")).astype(float)
        mass = {k: np.nan_to_num(fill(a[k]), nan=0) for k in ["mass_oil", "mass_evaporated", "mass_dispersed"]}
        assert all(np.isfinite(v).all() and (v >= -1e-5).all() for v in mass.values())
        series = dict(no_mar=(mass["mass_oil"] * ~coast).sum(0), na_costa=(mass["mass_oil"] * coast).sum(0),
                      evaporado=mass["mass_evaporated"].sum(0), disperso=mass["mass_dispersed"].sum(0))
        total = sum(series.values())
        assert total.max() > 0 and total[-1] > 0
        assert np.max(np.abs(total[hours >= p["horas_vazamento"]] - total[-1])) / total[-1] < .01, "Mass conservation outside 1% tolerance"
        arrival = float(hours[coast.any(axis=0)].min()) if coast.any() else None
        return a, coast, hours, series, dict(membro=p["membro"], regime=p["regime"], t_costa_h=arrival,
                                            frac_costa=float(coast[:, -1].mean()), final_mass_kg=float(total[-1]),
                                            simulation_hours=float(hours[-1]), terminal_state_carried_forward=bool(hours[-1] < p["horas_simuladas"]))


def aggregate():
    members = load("parameters.json")
    arrays = []; rows = []; balances = []
    hours = np.arange(load("scenario.json")["horas_simuladas"] + 1, dtype=float)
    for p in members:
        a, coast, h, mass, row = member_data(p)
        assert np.array_equal(h, hours[:len(h)]), "Mismatched time axes"
        rows.append(row)
        balances.append({key: np.interp(hours, h, value) for key, value in mass.items()})
        arrays.append((a["lon"], a["lat"]))
    finite_lon = np.concatenate([lo[np.isfinite(lo)] for lo, _ in arrays])
    finite_lat = np.concatenate([la[np.isfinite(la)] for _, la in arrays])
    resolution = .02
    bx = np.arange(min(finite_lon.min(), -43.45) - .1, max(finite_lon.max(), -42.4) + .1 + resolution, resolution)
    by = np.arange(min(finite_lat.min(), -23.45) - .1, max(finite_lat.max(), -22.7) + .1 + resolution, resolution)
    hits = np.zeros((len(by) - 1, len(bx) - 1), dtype=np.int32)
    for lon, lat in arrays:
        valid = np.isfinite(lon) & np.isfinite(lat)
        hist, _, _ = np.histogram2d(lat[valid], lon[valid], bins=[by, bx])
        hits += hist > 0
    xr.Dataset({"probability": (("latitude", "longitude"), hits / len(members)),
                "member_hits": (("latitude", "longitude"), hits)},
               coords={"latitude": (by[:-1] + by[1:]) / 2, "longitude": (bx[:-1] + bx[1:]) / 2},
               attrs={"members": len(members), "synthetic_forcings": 1, "interpretation": "fraction of ensemble members with any recorded oil position in each cell"}).to_netcdf("probability.nc")
    with open("arrival.csv", "w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with open("mass_balance.csv", "w") as f:
        w = csv.writer(f); w.writerow(["hours", "at_sea_kg", "coast_kg", "evaporated_kg", "dispersed_kg"])
        mean = np.array([[b[k] for k in ["no_mar", "na_costa", "evaporado", "disperso"]] for b in balances]).mean(0)
        w.writerows(zip(hours, *mean))
    selected = max(rows, key=lambda x: x["frac_costa"])
    shutil.copyfile(members[selected["membro"]]["saida"] + ".nc", "selected-member.nc")
    dump("summary.json", dict(members=len(members), members_reaching_coast=sum(x["t_costa_h"] is not None for x in rows),
                              selected_member=selected["membro"], selected_regime=selected["regime"],
                              maximum_coastal_fraction=selected["frac_costa"], grid_resolution_degrees=resolution,
                              bounds=[float(bx[0]), float(bx[-1]), float(by[0]), float(by[-1])], scenario=load("scenario.json"),
                              arrivals=rows, terminal_state_policy="Raw trajectories retain actual model duration; after all particles strand, terminal mass pools are held constant to the common analysis horizon without additional model integration.", warning="Synthetic constant wind/current forcings; not an operational spill forecast."))
    profiles = [load(f"profile-member-{p['membro']:03d}.json") for p in members]
    write_profiles(profiles)


def write_profiles(profiles):
    with open("perfil_tarefas.csv", "w") as f:
        columns = ["stage", "started_epoch", "finished_epoch", "duration_s", "cpu_s", "peak_rss_mb", "output_bytes"]
        w = csv.DictWriter(f, fieldnames=columns);w.writeheader();w.writerows({k: p[k] for k in columns} for p in profiles)


def base(ax):
    from roaring_landmask import RoaringLandmask
    bounds = load("summary.json")["bounds"]; x0, x1, y0, y1 = bounds
    gx = np.arange(x0, x1, .004); gy = np.arange(y0, y1, .004)
    assert len(gx) * len(gy) <= 8_000_000, "Map grid exceeds memory-safe display bounds"
    X, Y = np.meshgrid(gx, gy)
    land = RoaringLandmask.new().contains_many(X.ravel().astype("float64"), Y.ravel().astype("float64")).reshape(X.shape)
    ax.set_facecolor("#eaf2f8"); ax.contourf(X, Y, land, levels=[.5, 1.5], colors=["#d9d2c5"])
    ax.contour(X, Y, land, levels=[.5], colors="#7a7265", linewidths=.5)
    for name, lon, lat in [("Niterói", -43.07, -22.89), ("Rio de Janeiro", -43.42, -22.90), ("Maricá", -42.82, -22.90)]:
        if x0 < lon < x1 and y0 < lat < y1: ax.text(lon, lat, name, fontsize=8, ha="center")
    scenario = load("scenario.json");ax.plot(scenario["lon"], scenario["lat"], "k*", ms=12)
    ax.set(xlim=(x0, x1), ylim=(y0, y1), xlabel="Longitude", ylabel="Latitude")
    ax.set_aspect(1 / np.cos(np.radians((y0 + y1) / 2)))


def map_plot():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 7));base(ax)
    with xr.open_dataset("probability.nc") as ds:
        image = ax.pcolormesh(ds.longitude, ds.latitude, ds.probability.where(ds.probability > 0) * 100, shading="nearest", cmap="YlOrRd", vmin=0, vmax=100)
    fig.colorbar(image, ax=ax, label="Ensemble members visiting a cell (%)", shrink=.8)
    ax.set_title(f"OpenOil · {load('summary.json')['members']} members · synthetic forcings")
    fig.savefig("mapa_probabilidade.png", dpi=150, bbox_inches="tight");plt.close(fig)


def summary_plot():
    import matplotlib.pyplot as plt
    mass = np.genfromtxt("mass_balance.csv", delimiter=",", names=True)
    summary = load("summary.json");profiles = list(csv.DictReader(open("perfil_tarefas.csv")))
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    axes[0].stackplot(mass["hours"],*[mass[k]/1000 for k in ["at_sea_kg","coast_kg","evaporated_kg","dispersed_kg"]], labels=["At sea","Coast","Evaporated","Dispersed"])
    axes[0].set(xlabel="Simulated hours",ylabel="Oil mass (t)",title="Mean ensemble oil fate");axes[0].legend(fontsize=8)
    arrivals = sorted([r for r in summary["arrivals"] if r["t_costa_h"] is not None], key=lambda r:r["t_costa_h"])
    axes[1].barh([str(r["membro"]) for r in arrivals],[r["t_costa_h"] for r in arrivals]);axes[1].set(xlabel="Hours to first coast arrival",title=f"Coast arrival ({len(arrivals)}/{summary['members']})")
    origin = min(float(p["started_epoch"]) for p in profiles)
    for p in profiles:axes[2].barh(p["stage"],float(p["duration_s"]),left=float(p["started_epoch"])-origin,color="#4f8fba")
    axes[2].set(xlabel="Observed wall time (s)",title="Actual member execution timeline");axes[2].tick_params(axis="y",labelsize=6)
    fig.suptitle("OpenOil ensemble · synthetic forcings, real computation");fig.tight_layout();fig.savefig("resumo_workflow.png",dpi=140,bbox_inches="tight");plt.close(fig)


def animate():
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    summary = load("summary.json")
    p = load("parameters.json")[summary["selected_member"]]
    # The selected trajectory is an explicit aggregation output, not an external workspace lookup.
    with xr.open_dataset("selected-member.nc") as ds:
        lon=ds.lon.transpose("trajectory","time").values.copy();lat=ds.lat.transpose("trajectory","time").values.copy()
        status=ds.status.transpose("trajectory","time").values.copy();meanings=ds.status.attrs["flag_meanings"].split();values=ds.status.attrs.get("flag_values",range(len(meanings)))
        stranded=values[meanings.index("stranded")] if "stranded" in meanings else -1
    coast=fill(status)==stranded;lon_f=fill(lon);lat_f=fill(lat)
    fig,ax=plt.subplots(figsize=(8,6));base(ax)
    sea=ax.scatter([],[],s=3,color="#1f2933");shore=ax.scatter([],[],s=5,color="#d1495b")
    frames=list(range(0,lon.shape[1],max(1,(lon.shape[1]-1)//48)))
    if frames[-1]!=lon.shape[1]-1:frames.append(lon.shape[1]-1)
    def draw(k):
        active=np.isfinite(lon[:,k])&~coast[:,k];enc=coast[:,k]
        sea.set_offsets(np.c_[lon[active,k],lat[active,k]]);shore.set_offsets(np.c_[lon_f[enc,k],lat_f[enc,k]])
        ax.set_title(f"Member {p['membro']:02d} · {k} h · synthetic forcings")
        return sea,shore
    animation=FuncAnimation(fig,draw,frames=frames,interval=160,blit=False)
    animation.save("animacao.gif",writer=PillowWriter(fps=6));plt.close(fig)


def validate():
    from PIL import Image
    summary=load("summary.json");scenario=load("scenario.json");assert summary["members"]==scenario["members"]
    with xr.open_dataset("probability.nc") as ds:
        prob=ds.probability.values;hits=ds.member_hits.values
        assert np.isfinite(prob).all() and (prob>=0).all() and (prob<=1).all() and prob.max()>0
        assert np.allclose(prob,hits/summary["members"]) and (hits<=summary["members"]).all()
    for name in ["mapa_probabilidade.png","resumo_workflow.png","animacao.gif"]:
        with Image.open(name) as image:
            assert image.width>=500 and image.height>=300
            if name.endswith("gif"):assert image.n_frames>=2
            image.verify()
    names=["scenario.json","parameters.json","probability.nc","arrival.csv","mass_balance.csv","summary.json","perfil_tarefas.csv","selected-member.nc","mapa_probabilidade.png","resumo_workflow.png","animacao.gif"]
    for p in load("parameters.json"):
        member_data(p)
        names.extend([p["saida"]+".nc",f"profile-member-{p['membro']:03d}.json"])
    names.extend(["profile-prepare.json","profile-aggregate.json","profile-map.json","profile-summary.json","profile-animate.json"])
    digests={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in names}
    dump("manifest.json",dict(showcase=f"openoil-ensemble-{scenario['members']:02d}",status="success",artifacts=names,sha256=digests,
                              validation="real OpenOil trajectories, time axes, nonnegative conserved mass, probability bounds, decoded PNG and multi-frame GIF",synthetic_forcings=True))


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--stage",required=True);parser.add_argument("--members",type=int,default=8);parser.add_argument("--particles",type=int,default=1000);parser.add_argument("--hours",type=int,default=172)
    args=parser.parse_args();assert 1<=args.members<=64 and args.particles>=2 and args.hours>=2
    before={p.name:(p.stat().st_mtime_ns,p.stat().st_size) for p in Path(".").iterdir() if p.is_file()}
    started=time.time();cpu=time.process_time()
    if args.stage=="prepare":prepare(args)
    elif args.stage.startswith("member-"):simulate(int(args.stage.split("-")[1]))
    else:{"aggregate":aggregate,"map":map_plot,"summary":summary_plot,"animate":animate,"validate":validate}[args.stage]()
    finished=time.time()
    profile=dict(stage=args.stage,started_epoch=started,finished_epoch=finished,duration_s=finished-started,cpu_s=time.process_time()-cpu,peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,output_bytes=sum(p.stat().st_size for p in Path('.').iterdir() if p.is_file() and before.get(p.name)!=(p.stat().st_mtime_ns,p.stat().st_size)))
    dump(f"profile-{args.stage}.json",profile)
    if args.stage=="aggregate":write_profiles([load(f"profile-member-{i:03d}.json") for i in range(args.members)]+[profile])
    print(json.dumps({"stage":args.stage,"status":"completed","duration_s":finished-started}),flush=True)


if __name__=="__main__":main()
