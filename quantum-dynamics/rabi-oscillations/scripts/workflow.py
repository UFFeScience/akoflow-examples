#!/usr/bin/env python3
import argparse, csv, hashlib, json, math
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.integrate import solve_ivp

OMEGA=2*math.pi; DURATION=4.0; SAMPLES=4001; RTOL=1e-11; ATOL=1e-13; STEPS=(2e-3,1e-3)
CASES={"resonant":0.0,"half-detuned":0.5*OMEGA,"one-detuned":OMEGA,"two-detuned":2*OMEGA}

def dump(path,obj): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()
def rhs(delta):
    h=.5*np.array([[delta,OMEGA],[OMEGA,-delta]],dtype=np.complex128)
    return lambda _t,y:-1j*h@y
def solve(delta,step):
    t=np.linspace(0,DURATION,SAMPLES); result=solve_ivp(rhs(delta),(0,DURATION),np.array([1+0j,0+0j]),method="DOP853",t_eval=t,rtol=RTOL,atol=ATOL,max_step=step)
    if not result.success or result.y.shape!=(2,SAMPLES): raise RuntimeError(result.message)
    return t,result.y.T
def probability(t,delta):
    rate=math.hypot(OMEGA,delta); return (OMEGA/rate)**2*np.sin(.5*rate*t)**2
def bloch(state):
    a,b=state[:,0],state[:,1]
    return np.column_stack((2*np.real(np.conj(a)*b),2*np.imag(np.conj(a)*b),np.abs(a)**2-np.abs(b)**2))
def peak_frequency(t,p):
    ids=np.flatnonzero((p[1:-1]>p[:-2])&(p[1:-1]>=p[2:]))+1; peaks=[]
    for i in ids:
        y0,y1,y2=p[i-1:i+2]; denom=y0-2*y1+y2; offset=.5*(y0-y2)/denom if denom else 0.0; peaks.append(t[i]+offset*(t[i+1]-t[i]))
    if len(peaks)<4: raise RuntimeError("fewer than four peaks")
    return 1/float(np.mean(np.diff(peaks))),len(peaks)
def write_csv(path,t,state):
    p=np.abs(state[:,1])**2; b=bloch(state); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f,lineterminator="\n"); w.writerow(["time_s","a_real","a_imag","b_real","b_imag","excited_probability","bloch_x","bloch_y","bloch_z"])
        for row in zip(t,state[:,0].real,state[:,0].imag,state[:,1].real,state[:,1].imag,p,*b.T): w.writerow([format(float(x),".17g") for x in row])
def read_csv(path):
    d=np.genfromtxt(path,delimiter=",",names=True); t=d["time_s"]; state=np.column_stack((d["a_real"]+1j*d["a_imag"],d["b_real"]+1j*d["b_imag"])); return t,state

def prepare(out):
    dump(out/"inputs.json",{"acceptance":{"analytic_probability_max_abs":2e-9,"bloch_norm_error_max":3e-10,"frequency_relative_error_max":2e-4,"maximum_probability_error_max":2e-6,"norm_error_max":2e-10,"refinement_probability_max_abs":2e-10},"atol":ATOL,"cases_delta_rad_s":CASES,"citation":{"author":"Isidor Isaac Rabi","doi":"10.1103/PhysRev.51.652","title":"Space Quantization in a Gyrating Magnetic Field"},"duration_s":DURATION,"hamiltonian":"0.5*[[Delta,Omega],[Omega,-Delta]]; hbar=1","initial_state":["1+0i","0+0i"],"license":"MIT","max_steps_s":STEPS,"omega_rad_s":OMEGA,"rtol":RTOL,"sample_count":SAMPLES,"solver":"SciPy DOP853"})
def branch(out,case):
    delta=CASES[case]; t,s=solve(delta,STEPS[0]); tf,sf=solve(delta,STEPS[1]); p=np.abs(s[:,1])**2; pf=np.abs(sf[:,1])**2; exact=probability(t,delta); bv=bloch(s); freq,npeaks=peak_frequency(t,p); rate=math.hypot(OMEGA,delta); expected_freq=rate/(2*math.pi); expected_max=(OMEGA/rate)**2
    summary={"analytic_probability_max_abs_error":float(np.max(np.abs(p-exact))),"analytic_maximum_probability":expected_max,"bloch_norm_error_max":float(np.max(np.abs(np.linalg.norm(bv,axis=1)-1))),"case":case,"delta_rad_s":delta,"finite":bool(np.all(np.isfinite(s))),"frequency_cycles_s":freq,"frequency_peak_count":npeaks,"frequency_relative_error":abs(freq/expected_freq-1),"generalized_frequency_cycles_s":expected_freq,"maximum_probability":float(np.max(p)),"maximum_probability_error":abs(float(np.max(p))-expected_max),"norm_error_max":float(np.max(np.abs(np.sum(np.abs(s)**2,axis=1)-1))),"refinement_probability_max_abs":float(np.max(np.abs(p-pf))),"sample_count":SAMPLES}
    write_csv(out/"branches"/f"{case}.csv",t,s); dump(out/"branches"/f"{case}.json",summary); print(json.dumps(summary,sort_keys=True))
def aggregate(out):
    summaries={c:json.loads((out/"branches"/f"{c}.json").read_text()) for c in CASES}; checks={}
    for c,x in summaries.items():
        checks[f"{c}:finite"]=x["finite"]; checks[f"{c}:norm"]=x["norm_error_max"]<=2e-10; checks[f"{c}:bloch"]=x["bloch_norm_error_max"]<=3e-10; checks[f"{c}:analytic"]=x["analytic_probability_max_abs_error"]<=2e-9; checks[f"{c}:refinement"]=x["refinement_probability_max_abs"]<=2e-10; checks[f"{c}:frequency"]=x["frequency_relative_error"]<=2e-4; checks[f"{c}:maximum"]=x["maximum_probability_error"]<=2e-6
    checks["resonant:unit-transfer"]=summaries["resonant"]["maximum_probability"]>=.999999
    result={"checks":checks,"passed":all(checks.values()),"summaries":summaries}; dump(out/"rabi-scorecard.json",result)
    with (out/"rabi-scorecard.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f,lineterminator="\n"); w.writerow(["case","delta_rad_s","expected_frequency_cycles_s","measured_frequency_cycles_s","frequency_relative_error","expected_maximum_probability","measured_maximum_probability","analytic_probability_max_abs_error","norm_error_max"])
        for c,x in summaries.items(): w.writerow([c]+[format(float(x[k]),".17g") for k in ("delta_rad_s","generalized_frequency_cycles_s","frequency_cycles_s","frequency_relative_error","analytic_maximum_probability","maximum_probability","analytic_probability_max_abs_error","norm_error_max")])
    if not result["passed"]: raise RuntimeError("acceptance failed: "+", ".join(k for k,v in checks.items() if not v))
def render(out):
    data={c:read_csv(out/"branches"/f"{c}.csv") for c in CASES}; fig,ax=plt.subplots(figsize=(10,6),constrained_layout=True)
    for c,(t,s) in data.items(): ax.plot(t,np.abs(s[:,1])**2,label=c,lw=1.4)
    ax.set(xlabel="time (s)",ylabel="excited-state probability",ylim=(-.02,1.02),xlim=(0,DURATION),title="Generalized Rabi oscillations under detuning"); ax.grid(alpha=.25); ax.legend(); fig.savefig(out/"rabi-populations.png",dpi=150,metadata={"Software":"Akoflow Community Explorer"}); plt.close(fig)
    fig=plt.figure(figsize=(12,10));
    for i,(c,(t,s)) in enumerate(data.items()):
        ax=fig.add_subplot(2,2,i+1,projection="3d"); b=bloch(s); ax.plot(b[:,0],b[:,1],b[:,2],lw=1.2); ax.scatter([0],[0],[1],s=20,color="black"); ax.set(xlim=(-1,1),ylim=(-1,1),zlim=(-1,1),title=c); ax.set_box_aspect((1,1,1)); ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")
    fig.suptitle("Bloch-vector trajectories (unit sphere)"); fig.tight_layout(); fig.savefig(out/"bloch-trajectories.png",dpi=150,metadata={"Software":"Akoflow Community Explorer"}); plt.close(fig)
    frame_dir=out/".frames"; frame_dir.mkdir(exist_ok=True); paths=[]
    for frame,i in enumerate(np.linspace(0,SAMPLES-1,41,dtype=int)):
        fig,axes=plt.subplots(2,2,figsize=(10,7),constrained_layout=True)
        for ax,(c,(t,s)) in zip(axes.flat,data.items()): ax.plot(t,np.abs(s[:,1])**2,color="#1565c0"); ax.axvline(t[i],color="#c62828"); ax.scatter([t[i]],[abs(s[i,1])**2],color="#c62828",s=18); ax.set(xlim=(0,DURATION),ylim=(0,1.02),title=c,xlabel="time (s)",ylabel="P(excited)"); ax.grid(alpha=.2)
        fig.suptitle(f"Validated Rabi populations at t = {t[i]:.2f} s"); path=frame_dir/f"{frame:03d}.png"; fig.savefig(path,dpi=90,metadata={"Software":"Akoflow Community Explorer"}); plt.close(fig); paths.append(path)
    images=[Image.open(p).convert("P",palette=Image.Palette.ADAPTIVE,colors=128) for p in paths]; images[0].save(out/"rabi-oscillations.gif",save_all=True,append_images=images[1:],duration=120,loop=0,optimize=False,disposal=2)
    for x in images:x.close()
    for p in paths:p.unlink()
    frame_dir.rmdir()
def validate(out,reference=None):
    score=json.loads((out/"rabi-scorecard.json").read_text()); required=["inputs.json","rabi-scorecard.json","rabi-scorecard.csv","rabi-populations.png","bloch-trajectories.png","rabi-oscillations.gif"]+[f"branches/{c}.{e}" for c in CASES for e in ("csv","json")]; checks={"aggregate":score["passed"]}
    for r in required: checks[f"exists:{r}"]=(out/r).is_file() and (out/r).stat().st_size>0
    checks["png-signatures"]=all((out/r).read_bytes()[:8]==b"\x89PNG\r\n\x1a\n" for r in ("rabi-populations.png","bloch-trajectories.png")); checks["gif-signature"]=(out/"rabi-oscillations.gif").read_bytes()[:6] in (b"GIF87a",b"GIF89a")
    with Image.open(out/"rabi-oscillations.gif") as im: checks["gif-frames"]=im.n_frames==41
    if reference:
        for r in required: checks[f"deterministic:{r}"]=sha(out/r)==sha(reference/r)
    manifest={r:{"bytes":(out/r).stat().st_size,"sha256":sha(out/r)} for r in required}; result={"checks":checks,"manifest":manifest,"passed":all(checks.values())}; dump(out/"manifest.json",manifest); dump(out/"validation.json",result)
    if not result["passed"]: raise RuntimeError("validation failed")
    print(json.dumps({"passed":True,"checks":len(checks)},sort_keys=True))
def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="cmd",required=True)
    for n in ("prepare","aggregate","render"): s.add_parser(n).add_argument("--output",required=True)
    b=s.add_parser("branch"); b.add_argument("--output",required=True); b.add_argument("--case",choices=CASES,required=True)
    v=s.add_parser("validate"); v.add_argument("--output",required=True); v.add_argument("--reference")
    a=p.parse_args(); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    if a.cmd=="prepare":prepare(out)
    elif a.cmd=="branch":branch(out,a.case)
    elif a.cmd=="aggregate":aggregate(out)
    elif a.cmd=="render":render(out)
    else:validate(out,Path(a.reference) if a.reference else None)
if __name__=="__main__":main()
