#!/usr/bin/env python3
import argparse,csv,hashlib,json,math,os,platform
from pathlib import Path
import numpy as np

VERSION="community-jarzynski-v1"; SPEEDS=(.25,.5,.75,1.0); SHARDS=4; N=16384
SEED=20261123; H=.001; STEPS=1000; RETAIN=np.arange(0,1001,25)

def dump(path,obj):
    Path(path).write_text(json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n")
def label(v): return f"v{int(v*100):03d}"
def seed_table():
    root=np.random.SeedSequence(SEED); parents=root.spawn(len(SPEEDS)+2)
    children=[child for parent in parents for child in parent.spawn(SHARDS)]
    return [list(map(int,x.generate_state(4))) for x in children]
def rng_at(i): return np.random.Generator(np.random.PCG64DXSM(seed_table()[i]))
def simulate(v,n,h,rng,retain=False,innovations=None):
    steps=round(1/h); a=math.exp(-h); b=-v*(1-a); s=math.sqrt(1-a*a)
    y=rng.normal(size=n); work=np.zeros(n); traces=[]
    if retain: traces.append(work.copy())
    for j in range(1,steps+1):
        z=rng.normal(size=n) if innovations is None else innovations[j-1]
        yn=a*y+b+s*z; work += -.5*v*h*(y+yn); y=yn
        if retain and j%(steps//40)==0: traces.append(work.copy())
    return work, (np.stack(traces) if retain else None), y
def prepare(out):
    out.mkdir(parents=True,exist_ok=True)
    scenario={"workflow_version":VERSION,"model":"overdamped Brownian particle in translated harmonic trap","units":{"k":1,"gamma":1,"kBT":1,"beta":1},"speeds":list(SPEEDS),"tau":1,"step":H,"integrator":"exact OU state transition; trapezoidal inclusive work","trajectories_per_speed":N*SHARDS,"shards_per_speed":SHARDS,"trajectories_per_shard":N,"master_seed":SEED,"bit_generator":"NumPy PCG64DXSM 2.2.6","bootstrap":{"resamples":2000,"seed":SEED,"interval":"percentile 95%","guard_band":.01},"retained_times":[float(x/1000) for x in RETAIN],"delta_f":0,"publication_key":"community-explorer-issue-51-jarzynski-dragged-trap-v1","project_id":"44e9e6b5-454b-43b9-bf73-240be5e31aab"}
    dump(out/"input.json",scenario); dump(out/"seed-records.json",{"spawn_order":"six parent streams (four speeds, refinement, Euler), each spawning four child streams","states":seed_table()})
def shard(out,v,s):
    i=SPEEDS.index(v)*SHARDS+s; w,tr,y=simulate(v,N,H,rng_at(i),True)
    np.save(out/f"work-{label(v)}-s{s}.npy",w,allow_pickle=False)
    np.save(out/f"trace-{label(v)}-s{s}.npy",tr,allow_pickle=False)
    dump(out/f"shard-{label(v)}-s{s}.json",{"speed":v,"shard":s,"count":N,"finite":bool(np.isfinite(w).all() and np.isfinite(y).all()),"seed_state":seed_table()[i],"mean":float(w.mean()),"variance":float(w.var(ddof=1))})
def audit_step(out):
    rows=[]
    for si,v in enumerate(SPEEDS):
        rng=rng_at(16+si); fine=rng.normal(size=(2000,8192)); af=math.exp(-.0005)
        coarse=(af*fine[0::2]+fine[1::2])/math.sqrt(1+af*af)
        wf,_,_=simulate(v,8192,.0005,rng_at(16+si),innovations=fine)
        wc,_,_=simulate(v,8192,.001,rng_at(16+si),innovations=coarse)
        rows.append({"speed":v,"mean_difference":float(abs(wf.mean()-wc.mean())),"delta_f_difference":float(abs(-np.log(np.exp(-wf).mean())+np.log(np.exp(-wc).mean())))})
    dump(out/"time-step-audit.json",{"coupled_innovations":True,"rows":rows})
def audit_euler(out):
    rows=[]
    for si,v in enumerate(SPEEDS):
        rng=rng_at(20+si); n=2048; y=rng.normal(size=n); w=np.zeros(n)
        for _ in range(STEPS):
            yn=y+(-y-v)*H+math.sqrt(2*H)*rng.normal(size=n); w+=-.5*v*H*(y+yn); y=yn
        mu=v*v*math.exp(-1); var=2*mu; sem=math.sqrt(var/n); sevar=var*math.sqrt(2/(n-1))
        rows.append({"speed":v,"count":n,"mean":float(w.mean()),"variance":float(w.var(ddof=1)),"analytic_mean":mu,"analytic_variance":var,"mean_bound":4*sem,"variance_bound":4*sevar})
    dump(out/"euler-audit.json",{"method":"Euler-Maruyama","step":H,"rows":rows})
def aggregate(out):
    summaries=[]; conv={}; boot={}
    brng=np.random.Generator(np.random.PCG64DXSM(SEED))
    with (out/"work-summary.csv").open("w",newline="") as f:
      wr=csv.DictWriter(f,fieldnames=["speed","count","analytic_mean","mean","analytic_variance","variance","jarzynski_mean","delta_f_hat"]);wr.writeheader()
      for v in SPEEDS:
        arrays=[np.load(out/f"work-{label(v)}-s{s}.npy") for s in range(SHARDS)]; w=np.concatenate(arrays)
        if len(w)!=65536 or not np.isfinite(w).all(): raise RuntimeError("incomplete ensemble")
        mu=v*v*math.exp(-1); jm=float(np.exp(-w).mean()); df=float(-math.log(jm)); var=float(w.var(ddof=1)); mean=float(w.mean())
        row={"speed":v,"count":len(w),"analytic_mean":mu,"mean":mean,"analytic_variance":2*mu,"variance":var,"jarzynski_mean":jm,"delta_f_hat":df}; summaries.append(row);wr.writerow(row)
        sizes=[256,512,1024,2048,4096,8192,16384,32768,65536];conv[str(v)]=[{"n":n,"delta_f_hat":float(-np.log(np.exp(-w[:n]).mean()))} for n in sizes]
        vals=np.exp(-w); bs=np.empty(2000)
        for start in range(0,2000,20):
          idx=brng.integers(0,len(w),size=(20,len(w)));bs[start:start+20]=vals[idx].mean(axis=1)
        lo,hi=np.percentile(bs,[2.5,97.5]);boot[str(v)]={"lower":float(lo),"upper":float(hi),"guarded_lower":float(lo-.01),"guarded_upper":float(hi+.01)}
    dump(out/"jarzynski-estimates.json",{"rows":summaries,"bootstrap":boot,"convergence":conv})
def render(out):
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation,PillowWriter
    data=json.loads((out/"jarzynski-estimates.json").read_text()); rows=data["rows"]
    fig,axs=plt.subplots(2,2,figsize=(10,7))
    for ax,v in zip(axs.flat,SPEEDS):
      w=np.concatenate([np.load(out/f"work-{label(v)}-s{s}.npy") for s in range(4)]);mu=v*v/math.e;sig=math.sqrt(2*mu);x=np.linspace(mu-4*sig,mu+4*sig,300)
      ax.hist(w,bins=70,density=True,alpha=.65,color="#111");ax.plot(x,np.exp(-.5*((x-mu)/sig)**2)/(sig*math.sqrt(2*math.pi)),color="#d62728");ax.set_title(f"v={v:.2f}");ax.set_xlabel("work W");ax.set_ylabel("density")
    fig.tight_layout();fig.savefig(out/"work-distributions.png",dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5))
    for v in SPEEDS: ax.plot([x["n"] for x in data["convergence"][str(v)]],[x["delta_f_hat"] for x in data["convergence"][str(v)]],marker="o",label=f"v={v:.2f}")
    ax.axhline(0,color="black",lw=1);ax.set_xscale("log",base=2);ax.set_xlabel("trajectories");ax.set_ylabel("estimated ΔF");ax.legend();fig.tight_layout();fig.savefig(out/"free-energy-convergence.png",dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5));vs=np.array(SPEEDS);ax.plot(vs,[r["mean"] for r in rows],"o-",label="empirical");ax.plot(vs,vs*vs/math.e,"--",label="exact");ax.set_xlabel("trap speed v");ax.set_ylabel("mean dissipated work");ax.legend();fig.tight_layout();fig.savefig(out/"dissipated-work-scaling.png",dpi=150);plt.close(fig)
    traces={v:np.concatenate([np.load(out/f"trace-{label(v)}-s{s}.npy") for s in range(4)],axis=1) for v in SPEEDS}
    fig,axs=plt.subplots(2,2,figsize=(9,7))
    def frame(k):
      for ax,v in zip(axs.flat,SPEEDS):
        ax.clear();w=traces[v][k];ax.hist(w,bins=45,density=True,color="#222",alpha=.75);df=-np.log(np.exp(-w).mean());ax.set_title(f"v={v:.2f}, t={k/40:.3f}, ΔF̂={df:.4f}");ax.set_xlabel("accumulated work")
      fig.tight_layout()
    FuncAnimation(fig,frame,frames=41).save(out/"jarzynski-convergence.gif",writer=PillowWriter(fps=5));plt.close(fig)
def validate(out,reference=None):
    rows=json.loads((out/"jarzynski-estimates.json").read_text())["rows"]; boot=json.loads((out/"jarzynski-estimates.json").read_text())["bootstrap"]
    checks={}
    checks["complete"]=all(r["count"]==65536 for r in rows)
    checks["means"]=all(abs(r["mean"]-r["analytic_mean"])<=max(.005,4*math.sqrt(r["analytic_variance"]/r["count"])) for r in rows)
    checks["variances"]=all(abs(r["variance"]/r["analytic_variance"]-1)<=.03 for r in rows)
    checks["jarzynski"]=all(abs(r["delta_f_hat"])<=.015 and boot[str(r["speed"])]["guarded_lower"]<=1<=boot[str(r["speed"])]["guarded_upper"] for r in rows)
    means=np.array([r["mean"] for r in rows]);checks["scaling"]=bool(np.all(np.diff(means)>0) and np.all(abs((means/means[0])/np.array([1,4,9,16])-1)<=.04))
    ta=json.loads((out/"time-step-audit.json").read_text());checks["time_step"]=all(r["mean_difference"]<=.003 and r["delta_f_difference"]<=.003 for r in ta["rows"])
    ea=json.loads((out/"euler-audit.json").read_text());checks["euler"]=all(abs(r["mean"]-r["analytic_mean"])<=r["mean_bound"] and abs(r["variance"]-r["analytic_variance"])<=r["variance_bound"] for r in ea["rows"])
    from PIL import Image
    required=["work-distributions.png","free-energy-convergence.png","dissipated-work-scaling.png","jarzynski-convergence.gif"]
    checks["media"]=all((out/x).stat().st_size>1000 for x in required) and getattr(Image.open(out/required[-1]),"n_frames",1)==41
    deterministic=None
    if reference:
      names=[p.name for p in out.iterdir() if p.suffix in {".json",".csv",".npy",".png",".gif"} and p.name!="validation.json"]
      deterministic=all(hashlib.sha256((out/n).read_bytes()).digest()==hashlib.sha256((reference/n).read_bytes()).digest() for n in names)
      checks["deterministic"]=deterministic
    dump(out/"validation.json",{"overall_pass":all(checks.values()),"checks":checks,"environment":{"python":platform.python_version(),"numpy":np.__version__,"platform":platform.platform()},"limitations":["one-dimensional overdamped harmonic model","dimensionless units","translation gives ΔF=0","finite-sample exponential estimator"]})
    if not all(checks.values()): raise SystemExit("validation failed: "+repr(checks))
def main():
 p=argparse.ArgumentParser();p.add_argument("command");p.add_argument("--output",required=True);p.add_argument("--speed",type=float);p.add_argument("--shard",type=int);p.add_argument("--reference");a=p.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=True)
 {"prepare":lambda:prepare(o),"shard":lambda:shard(o,a.speed,a.shard),"audit-step":lambda:audit_step(o),"audit-euler":lambda:audit_euler(o),"aggregate":lambda:aggregate(o),"render":lambda:render(o),"validate":lambda:validate(o,Path(a.reference) if a.reference else None)}[a.command]()
if __name__=="__main__":main()
