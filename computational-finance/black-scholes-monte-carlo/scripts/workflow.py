import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np

SEEDS=(20261123,20261124,20261125,20261126)
GRID=(1024,4096,16384,65536,250000)
N=250000
S0=K=100.0; R=.05; SIGMA=.2; T=1.0
CALL=10.450583572185565; PUT=5.573526022256971; PARITY=4.877057549928594

def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")

def oracle():
    d1=(math.log(S0/K)+(R+.5*SIGMA**2)*T)/(SIGMA*math.sqrt(T)); d2=d1-SIGMA*math.sqrt(T)
    cdf=lambda x:.5*(1+math.erf(x/math.sqrt(2)))
    call=S0*cdf(d1)-K*math.exp(-R*T)*cdf(d2)
    put=K*math.exp(-R*T)*cdf(-d2)-S0*cdf(-d1)
    return call,put,S0-K*math.exp(-R*T)

def prepare(out):
    call,put,parity=oracle()
    scenario={"S0":S0,"K":K,"r":R,"sigma":SIGMA,"T":T,"samples_per_branch":N,"seeds":list(SEEDS),"grid":list(GRID),"rng":"NumPy PCG64"}
    write_json(out/"scenario.json",scenario)
    write_json(out/"analytic-oracle.json",{"call":call,"put":put,"parity":parity,"deltas":{"call":call-CALL,"put":put-PUT,"parity":parity-PARITY}})
    write_json(out/"provenance.json",{"code_license":"Apache-2.0","input_license":"CC0-1.0","paper":{"authors":["Fischer Black","Myron Scholes"],"title":"The Pricing of Options and Corporate Liabilities","doi":"10.1086/260062"},"adaptation":"Independent risk-neutral Monte Carlo audit; no paper content redistributed"})

def row_stats(x):
    return len(x),float(x.sum()),float(np.square(x).sum())

def estimate(out,seed):
    if seed not in SEEDS: raise SystemExit("undeclared seed")
    rng=np.random.Generator(np.random.PCG64(seed)); z=rng.standard_normal(N)
    st=S0*np.exp((R-.5*SIGMA**2)*T+SIGMA*math.sqrt(T)*z); disc=math.exp(-R*T)
    call=disc*np.maximum(st-K,0); put=disc*np.maximum(K-st,0); paired=call-put
    rows=[]
    for n in GRID:
        vals=[]
        for name,x in (("call",call[:n]),("put",put[:n]),("parity",paired[:n]),("terminal",st[:n])):
            count,total,total2=row_stats(x); mean=total/count; var=(total2-total*total/count)/(count-1); vals += [mean,math.sqrt(var/count)] if name!="terminal" else [mean,var]
        rows.append([n]+vals)
    d=out/"branches"; d.mkdir(parents=True,exist_ok=True)
    with (d/f"seed-{seed}.csv").open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["n","call_mean","call_se","put_mean","put_se","parity_mean","parity_se","terminal_mean","terminal_variance"]); w.writerows(rows)
    stats={name:{"count":v[0],"sum":v[1],"sum_squares":v[2]} for name,x in (("call",call),("put",put),("parity",paired),("terminal",st)) for v in [row_stats(x)]}
    write_json(d/f"seed-{seed}.json",{"seed":seed,"rng":"PCG64","stats":stats,"visualization_terminal_prices":st[:256].tolist()})

def merge(stats,name):
    parts=[x["stats"][name] for x in stats]; n=sum(p["count"] for p in parts); s=sum(p["sum"] for p in parts); q=sum(p["sum_squares"] for p in parts); mean=s/n; var=(q-s*s/n)/(n-1)
    return {"count":n,"sum":s,"sum_squares":q,"mean":mean,"variance":var,"standard_error":math.sqrt(var/n)}

def aggregate(out):
    branches=[json.loads((out/"branches"/f"seed-{s}.json").read_text()) for s in SEEDS]
    merged={name:merge(branches,name) for name in ("call","put","parity","terminal")}
    curves=[]
    for n in GRID:
        rows=[next(csv.DictReader((out/"branches"/f"seed-{s}.csv").open())) for s in ()] # keep parser deterministic
        samples=[]
        for seed in SEEDS:
            allrows=list(csv.DictReader((out/"branches"/f"seed-{seed}.csv").open())); samples.append(next(r for r in allrows if int(r["n"])==n))
        item={"n_per_branch":n,"n_total":4*n}
        for kind in ("call","put"):
            means=np.array([float(r[f"{kind}_mean"]) for r in samples]); ses=np.array([float(r[f"{kind}_se"]) for r in samples]); item[f"{kind}_mean"]=float(means.mean()); item[f"{kind}_se"]=float(math.sqrt(np.square(ses).sum())/4)
        curves.append(item)
    slopes={kind:float(np.polyfit(np.log([x["n_total"] for x in curves]),np.log([x[f"{kind}_se"] for x in curves]),1)[0]) for kind in ("call","put")}
    exact_mean=S0*math.exp(R*T); exact_var=S0**2*math.exp(2*R*T)*(math.exp(SIGMA**2*T)-1)
    m1=S0*math.exp(R*T); m2=S0**2*math.exp(2*R*T+SIGMA**2*T); m3=S0**3*math.exp(3*R*T+3*SIGMA**2*T); m4=S0**4*math.exp(4*R*T+6*SIGMA**2*T)
    mu4=m4-4*m1*m3+6*m1*m1*m2-3*m1**4; nt=4*N; variance_tolerance=4*math.sqrt((mu4-((nt-3)/(nt-1))*exact_var**2)/nt)
    checks={"call_price":abs(merged["call"]["mean"]-CALL)<=max(4*merged["call"]["standard_error"],.03),"put_price":abs(merged["put"]["mean"]-PUT)<=max(4*merged["put"]["standard_error"],.03),"paired_parity":abs(merged["parity"]["mean"]-PARITY)<=4*merged["parity"]["standard_error"],"call_slope":-.55<=slopes["call"]<=-.45,"put_slope":-.55<=slopes["put"]<=-.45,"terminal_mean":abs(merged["terminal"]["mean"]-exact_mean)<=4*merged["terminal"]["standard_error"],"terminal_variance":abs(merged["terminal"]["variance"]-exact_var)<=variance_tolerance}
    result={"merged":merged,"oracle":{"call":CALL,"put":PUT,"parity":PARITY,"terminal_mean":exact_mean,"terminal_variance":exact_var},"errors":{"call":merged["call"]["mean"]-CALL,"put":merged["put"]["mean"]-PUT,"parity":merged["parity"]["mean"]-PARITY,"terminal_variance":merged["terminal"]["variance"]-exact_var},"slopes":slopes,"variance_tolerance":variance_tolerance,"curves":curves,"checks":checks,"passed":all(checks.values())}
    write_json(out/"aggregate.json",result)
    with (out/"convergence.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(curves[0]));w.writeheader();w.writerows(curves)
    if not result["passed"]: raise SystemExit("scientific gate failed")

def render(out):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation,PillowWriter
    result=json.loads((out/"aggregate.json").read_text()); curves=result["curves"]
    ns=np.array([x["n_total"] for x in curves])
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,kind,truth in zip(axes,("call","put"),(CALL,PUT)):
        means=np.array([x[f"{kind}_mean"] for x in curves]); se=np.array([x[f"{kind}_se"] for x in curves]); ax.errorbar(ns,means,yerr=1.96*se,marker="o",capsize=3);ax.axhline(truth,color="black",ls="--",label="analytic");ax.set_xscale("log");ax.set(xlabel="aggregate samples",ylabel="discounted price",title=f"{kind.title()} convergence");ax.legend()
    fig.tight_layout();fig.savefig(out/"price-convergence.png",dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,5))
    for kind in ("call","put"): ax.loglog(ns,[x[f"{kind}_se"] for x in curves],"o-",label=f"{kind}, slope {result['slopes'][kind]:.3f}")
    ref=np.array([x["call_se"] for x in curves]);ax.loglog(ns,ref[0]*(ns/ns[0])**-.5,"--",color="gray",label=r"$N^{-1/2}$");ax.set(xlabel="aggregate samples",ylabel="standard error",title="Monte Carlo uncertainty scaling");ax.legend();fig.tight_layout();fig.savefig(out/"standard-error-scaling.png",dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5));lines={};
    for kind,color,truth in (("call","tab:blue",CALL),("put","tab:orange",PUT)):
        ax.axhline(truth,color=color,ls="--",alpha=.6);lines[kind]=ax.errorbar([],[],yerr=[],marker="o",color=color,label=kind)
    ax.set_xscale("log");ax.set_xlim(ns[0]*.8,ns[-1]*1.2);ax.set_ylim(5.2,10.8);ax.set(xlabel="aggregate samples",ylabel="discounted price",title="Cumulative risk-neutral estimates");ax.legend()
    def update(i):
        ax.collections.clear() if False else None
        for artist in list(ax.lines):
            if artist.get_marker()=="o": artist.remove()
        for kind,color in (("call","tab:blue"),("put","tab:orange")):
            means=[x[f"{kind}_mean"] for x in curves[:i+1]];se=[x[f"{kind}_se"] for x in curves[:i+1]];ax.errorbar(ns[:i+1],means,yerr=1.96*np.array(se),marker="o",color=color,capsize=3)
        ax.set_title(f"Cumulative estimates through N={ns[i]:,}");return ax,
    ani=FuncAnimation(fig,update,frames=len(curves),blit=False);ani.save(out/"option-convergence.gif",writer=PillowWriter(fps=1));plt.close(fig)

def validate(out,reference=None):
    required=["scenario.json","analytic-oracle.json","provenance.json","aggregate.json","convergence.csv","price-convergence.png","standard-error-scaling.png","option-convergence.gif"]+[f"branches/seed-{s}.csv" for s in SEEDS]+[f"branches/seed-{s}.json" for s in SEEDS]
    missing=[p for p in required if not (out/p).is_file()]; result=json.loads((out/"aggregate.json").read_text())
    from PIL import Image
    gif=Image.open(out/"option-convergence.gif"); hashes={p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in required}
    checks={"missing":missing,"scientific_pass":result["passed"],"gif_frames":gif.n_frames,"gif_multiframe":gif.n_frames>1,"finite":all(math.isfinite(v) for k in ("call","put","parity","terminal") for v in result["merged"][k].values() if isinstance(v,(int,float))),"assumptions":["continuous trading","constant risk-free rate","constant volatility","lognormal terminal price","no dividends","frictionless market","European exercise","no empirical market validation"]}
    if reference: checks["reference_match"] = hashes=={p:hashlib.sha256((reference/p).read_bytes()).hexdigest() for p in required}
    checks["passed"]=not missing and checks["scientific_pass"] and checks["gif_multiframe"] and checks["finite"] and checks.get("reference_match",True)
    write_json(out/"checksums.json",hashes);write_json(out/"validation.json",checks)
    if not checks["passed"]:raise SystemExit("validation failed")

def main():
    p=argparse.ArgumentParser();p.add_argument("command",choices=["prepare","estimate","aggregate","render","validate"]);p.add_argument("--output",required=True);p.add_argument("--seed",type=int);p.add_argument("--reference");a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    {"prepare":lambda:prepare(out),"estimate":lambda:estimate(out,a.seed),"aggregate":lambda:aggregate(out),"render":lambda:render(out),"validate":lambda:validate(out,Path(a.reference) if a.reference else None)}[a.command]()
if __name__=="__main__":main()
