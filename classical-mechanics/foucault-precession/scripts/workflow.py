#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp

G=9.80665; LENGTH=67.; X0=3.; DAY=86164.0905; OMEGA_E=2*np.pi/DAY
LATITUDES=(-60,-30,0,30,60); W0=np.sqrt(G/LENGTH); PERIOD=2*np.pi/W0

def dump(path, value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def exact(t,omega):
    root=np.sqrt(omega*omega+W0*W0); alpha=-omega+root; beta=omega+root
    z=X0*(beta*np.exp(1j*alpha*t)+alpha*np.exp(-1j*beta*t))/(alpha+beta)
    zd=1j*X0*alpha*beta*(np.exp(1j*alpha*t)-np.exp(-1j*beta*t))/(alpha+beta)
    return np.column_stack((z.real,z.imag,zd.real,zd.imag))
def prepare(out):
    scenario={"g_m_s2":G,"length_m":LENGTH,"x0_m":X0,"initial_velocity_m_s":[0,0],"sidereal_day_s":DAY,"latitudes_deg":LATITUDES,"model":"linear planar small-angle Foucault pendulum","source_doi":"10.1590/1806-9126-RBEF-2019-0274"}
    canonical=json.dumps(scenario,sort_keys=True,separators=(",",":" )).encode(); scenario["canonical_sha256"]=hashlib.sha256(canonical).hexdigest(); dump(out/"inputs.json",scenario)
def integrate(max_step,omega):
    def rhs(_,q): return (q[2],q[3],-W0*W0*q[0]+2*omega*q[3],-W0*W0*q[1]-2*omega*q[2])
    def peak(_,q): return q[0]*q[2]+q[1]*q[3]
    peak.direction=-1; peak.terminal=False
    t=np.linspace(0,DAY,20001)
    sol=solve_ivp(rhs,(0,DAY),(X0,0,0,0),method="DOP853",rtol=2e-12,atol=2e-13,max_step=max_step,t_eval=t,events=peak)
    peaks=sol.y_events[0]
    angles=np.unwrap(2*np.arctan2(peaks[:,1],peaks[:,0]))/2; times=sol.t_events[0]
    slope,intercept=np.polyfit(times,angles,1)
    return t,sol.y.T,float(slope),float(intercept),len(peaks)
def branch(out,lat):
    omega=OMEGA_E*np.sin(np.deg2rad(lat)); t,q,rate,offset,n=integrate(PERIOD/20,omega); _,q2,rate2,offset2,_=integrate(PERIOD/40,omega); ref=exact(t,omega)
    data={"latitude_deg":lat,"omega_rad_s":omega,"expected_rate_rad_s":-omega,"fitted_rate_rad_s":rate,"refined_rate_rad_s":rate2,"rate_refinement_delta_rad_s":abs(rate-rate2),"final_orientation_rad":rate*DAY+offset,"refined_final_orientation_rad":rate2*DAY+offset2,"final_orientation_delta_rad":abs((rate*DAY+offset)-(rate2*DAY+offset2)),"max_exact_error_m":float(np.max(np.abs(q-ref))),"turning_points":n,"finite":bool(np.isfinite(q).all())}
    np.savez_compressed(out/f"latitude-{lat:+03d}.npz",t=t,state=q,exact=ref); dump(out/f"latitude-{lat:+03d}.json",data)
def aggregate(out):
    rows=[json.loads((out/f"latitude-{lat:+03d}.json").read_text()) for lat in LATITUDES]
    rates={r["latitude_deg"]:r["fitted_rate_rad_s"] for r in rows}; expected={lat:-OMEGA_E*np.sin(np.deg2rad(lat)) for lat in LATITUDES}
    checks={"finite_exact":all(r["finite"] and r["max_exact_error_m"]<=1e-7 for r in rows),"rates":all(abs(rates[x]-expected[x])/abs(expected[x])<=1e-5 for x in LATITUDES if x),"equator":abs(rates[0])<=1e-12,"symmetry":all(abs(abs(rates[x])-abs(rates[-x]))/abs(rates[x])<=1e-10 and rates[x]*rates[-x]<0 for x in (30,60)),"ratio":bool(abs(abs(rates[60]/rates[30])-np.sin(np.deg2rad(60))/np.sin(np.deg2rad(30)))/(np.sin(np.deg2rad(60))/np.sin(np.deg2rad(30)))<=1e-5),"refinement":all(r["rate_refinement_delta_rad_s"]<=1e-10 and r["final_orientation_delta_rad"]<=1e-6 for r in rows),"small_angle":X0/LENGTH<.05}
    dump(out/"metrics.json",{"branches":rows,"checks":checks,"passed":all(checks.values())})
def render(out):
    import matplotlib.pyplot as plt
    from PIL import Image
    rows=json.loads((out/"metrics.json").read_text())["branches"]
    fig,axs=plt.subplots(1,2,figsize=(11,5))
    for lat in LATITUDES:
        z=np.load(out/f"latitude-{lat:+03d}.npz"); stride=20; axs[0].plot(z["state"][::stride,0],z["state"][::stride,1],lw=.7,label=f"{lat:+d}°")
    axs[0].set(xlabel="x (m)",ylabel="y (m)",title="One sidereal day of plane rotation",aspect="equal"); axs[0].legend()
    l=np.array(LATITUDES); measured=np.array([r["fitted_rate_rad_s"] for r in rows]); axs[1].plot(l,-OMEGA_E*np.sin(np.deg2rad(l)),"k-",label="−Ωₑ sin λ"); axs[1].plot(l,measured,"o",color="#777",label="numerical fit"); axs[1].set(xlabel="latitude (degrees)",ylabel="signed rate (rad/s)",title="Latitude-precession law"); axs[1].legend(); fig.tight_layout(); fig.savefig(out/"foucault-trajectories.png",dpi=160); plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,5)); ax.plot(l,measured,"o-",color="#222"); ax.axhline(0,color="#999",lw=.8); ax.set(xlabel="latitude (degrees)",ylabel="fitted precession (rad/s)",title="Signed Foucault precession"); fig.tight_layout(); fig.savefig(out/"precession-vs-latitude.png",dpi=160); plt.close(fig)
    states={lat:np.load(out/f"latitude-{lat:+03d}.npz")["state"] for lat in LATITUDES}; frames=[]
    for idx in np.linspace(0,20000,48,dtype=int):
        fig,ax=plt.subplots(figsize=(6,6));
        for lat in LATITUDES:
            v=states[lat][idx,:2]; u=v/np.linalg.norm(v); ax.plot((-3*u[0],3*u[0]),(-3*u[1],3*u[1]),label=f"{lat:+d}°")
        ax.set(xlim=(-3.3,3.3),ylim=(-3.3,3.3),aspect="equal",xlabel="x (m)",ylabel="y (m)",title=f"Oscillation planes, t={idx*DAY/20000/3600:.1f} h"); ax.legend(loc="upper right",fontsize=7); fig.tight_layout(); fig.canvas.draw(); frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert("P")); plt.close(fig)
    frames[0].save(out/"foucault-precession.gif",save_all=True,append_images=frames[1:],duration=120,loop=0)
def validate(out,reference=None):
    metrics=json.loads((out/"metrics.json").read_text()); gallery=all((out/x).stat().st_size>1000 for x in ("foucault-trajectories.png","precession-vs-latitude.png","foucault-precession.gif")); repeat=True
    if reference: repeat=all((out/f"latitude-{lat:+03d}.json").read_bytes()==(reference/f"latitude-{lat:+03d}.json").read_bytes() for lat in LATITUDES)
    passed=metrics["passed"] and gallery and repeat; dump(out/"validation.json",{"passed":passed,"checks":metrics["checks"],"gallery":gallery,"byte_identical_branch_json":repeat})
    files=[p for p in out.iterdir() if p.is_file() and p.name!="manifest.json"]; dump(out/"manifest.json",{"files":[{"path":p.name,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]})
    if not passed: raise SystemExit(1)
def main():
    p=argparse.ArgumentParser(); p.add_argument("mode",choices=("prepare","branch","aggregate","render","validate")); p.add_argument("--output",required=True); p.add_argument("--latitude",type=int,choices=LATITUDES); p.add_argument("--reference"); a=p.parse_args(); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    {"prepare":lambda:prepare(out),"branch":lambda:branch(out,a.latitude),"aggregate":lambda:aggregate(out),"render":lambda:render(out),"validate":lambda:validate(out,Path(a.reference) if a.reference else None)}[a.mode]()
if __name__=="__main__": main()
