import argparse, csv, hashlib, json, os
from pathlib import Path
import numpy as np
from numba import njit
from scipy.stats import binom

SIZES=(32,64,128,256); SHARDS=4; PER_SHARD=1024; SEED=20261123; PAPER=0.59274621
PGRID=np.arange(.5700,.6150+.00025,.0005)

def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")

@njit(cache=False)
def first_span(order,L):
    N=L*L; parent=np.full(N,-1,np.int32); sizes=np.ones(N,np.int32); bits=np.zeros(N,np.uint8)
    for step in range(N):
        site=order[step]; row=site//L; col=site-row*L; parent[site]=site; mask=0
        if col==0: mask|=1
        if col==L-1: mask|=2
        if row==0: mask|=4
        if row==L-1: mask|=8
        bits[site]=mask
        for nb in (site-1,site+1,site-L,site+L):
            if nb<0 or nb>=N or parent[nb]<0: continue
            if (nb==site-1 and col==0) or (nb==site+1 and col==L-1): continue
            a=site
            while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
            b=nb
            while parent[b]!=b: parent[b]=parent[parent[b]]; b=parent[b]
            if a!=b:
                if sizes[a]<sizes[b]: a,b=b,a
                parent[b]=a; sizes[a]+=sizes[b]; bits[a]|=bits[b]
        root=site
        while parent[root]!=root: root=parent[root]
        m=bits[root]
        if (m&3)==3 or (m&12)==12: return step+1
    return N

def seeds(): return [s.spawn(SHARDS) for s in np.random.SeedSequence(SEED).spawn(len(SIZES))]
def rng_for(L,shard): return np.random.Generator(np.random.PCG64DXSM(seeds()[SIZES.index(L)][shard]))

def prepare(out):
    scenario={"sizes":list(SIZES),"shards_per_size":SHARDS,"realizations_per_shard":PER_SHARD,"master_seed":SEED,"rng":"PCG64DXSM","boundaries":"open","neighbors":4,"probability_grid":[.57,.615,.0005],"bootstrap_resamples":2000,"bootstrap_seed":SEED,"paper_pc":PAPER,"fit":"p50(L)=pc+a*L^(-3/4)"}
    scenario["spawn_keys"]={str(L):[list(s.spawn_key) for s in ss] for L,ss in zip(SIZES,seeds())}
    write_json(out/"input.json",scenario)
    write_json(out/"provenance.json",{"method":"Newman-Ziff incremental site occupation with union by size/path compression","code_license":"MIT","paper":"10.1103/PhysRevLett.85.4104","method_paper":"10.1103/PhysRevE.64.016706"})

def shard(out,L,index):
    rng=rng_for(L,index); vals=np.empty(PER_SHARD,np.int32); first_span(np.arange(16,dtype=np.int32),4)
    for i in range(PER_SHARD): vals[i]=first_span(rng.permutation(L*L).astype(np.int32,copy=False),L)
    d=out/"shards"; d.mkdir(parents=True,exist_ok=True); np.save(d/f"l{L:03d}-s{index}.npy",vals,allow_pickle=False)
    write_json(d/f"l{L:03d}-s{index}.json",{"L":L,"shard":index,"count":PER_SHARD,"minimum":int(vals.min()),"maximum":int(vals.max()),"spawn_key":list(seeds()[SIZES.index(L)][index].spawn_key)})

def p50(curve):
    i=int(np.searchsorted(curve,.5)); x0,x1=PGRID[i-1:i+1]; y0,y1=curve[i-1:i+1]; return float(x0+(.5-y0)*(x1-x0)/(y1-y0))

def bfs(occ,L):
    grid=occ.reshape(L,L)
    for g in (grid,grid.T):
        seen=np.zeros_like(g,bool); stack=[(r,0) for r in range(L) if g[r,0]]
        for pos in stack: seen[pos]=True
        k=0
        while k<len(stack):
            r,c=stack[k]; k+=1
            if c==L-1:return True
            for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if 0<=rr<L and 0<=cc<L and g[rr,cc] and not seen[rr,cc]:seen[rr,cc]=True;stack.append((rr,cc))
    return False

def aggregate(out):
    counts={L:np.concatenate([np.load(out/"shards"/f"l{L:03d}-s{s}.npy",allow_pickle=False) for s in range(SHARDS)]) for L in SIZES}
    contrib={L:binom.sf(counts[L][:,None]-1,L*L,PGRID[None,:]) for L in SIZES}; curves={L:contrib[L].mean(0) for L in SIZES}
    p50s={L:p50(curves[L]) for L in SIZES}; slopes={}
    for L in SIZES:
        lo=np.interp(p50s[L]-.002,PGRID,curves[L]); hi=np.interp(p50s[L]+.002,PGRID,curves[L]); slopes[L]=float((hi-lo)/.004)
    x=np.array([L**(-.75) for L in SIZES]); pc=float(np.polyfit(x,[p50s[L] for L in SIZES],1)[1]); brng=np.random.Generator(np.random.PCG64DXSM(SEED)); boot=np.empty(2000)
    for b in range(2000):
        ps=[p50(contrib[L][brng.integers(0,4096,4096)].mean(0)) for L in SIZES]; boot[b]=np.polyfit(x,ps,1)[1]
    ci=np.percentile(boot,[2.5,97.5]); audits=[]
    for L in SIZES:
        rng=rng_for(L,0)
        for rid in range(PER_SHARD):
            order=rng.permutation(L*L).astype(np.int32,copy=False)
            if rid not in (0,341,682,1023):continue
            threshold=first_span(order,L)
            for p in (.57,.59,.60,.615):
                n=round(p*L*L); occ=np.zeros(L*L,bool);occ[order[:n]]=True; audits.append((threshold<=n)==bfs(occ,L))
    checks={"all_realizations":all(len(counts[L])==4096 and np.all((counts[L]>=L)&(counts[L]<=L*L)) for L in SIZES),"curves":all(np.all(np.isfinite(curves[L])) and np.min(np.diff(curves[L]))>=-2e-12 and curves[L][0]<.5<curves[L][-1] for L in SIZES),"p50_range":all(.57<=p50s[L]<=.615 for L in SIZES),"pc_tolerance":abs(pc-PAPER)<=.003,"guarded_interval":ci[0]-.0015<=PAPER<=ci[1]+.0015,"sharpening":slopes[256]/slopes[32]>=2,"flood_fill_audit":len(audits)==64 and all(audits)}
    result={"p50":{str(L):p50s[L] for L in SIZES},"slopes":{str(L):slopes[L] for L in SIZES},"pc":pc,"paper_pc":PAPER,"absolute_error":abs(pc-PAPER),"bootstrap_95":ci.tolist(),"slope_ratio_256_32":slopes[256]/slopes[32],"checks":{k:bool(v) for k,v in checks.items()},"passed":bool(all(checks.values()))}
    write_json(out/"threshold-fit.json",result)
    with (out/"spanning-curves.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["p"]+[f"L{L}" for L in SIZES]);w.writerows([[f"{p:.4f}"]+[f"{curves[L][i]:.12f}" for L in SIZES] for i,p in enumerate(PGRID)])
    write_json(out/"connectivity-audit.json",{"comparisons":len(audits),"all_agree":all(audits)})
    if not result["passed"]:raise SystemExit("fixed scientific gate failed")

def spanning_component(occ,L):
    grid=occ.reshape(L,L); seen=np.zeros(L*L,bool)
    for start in np.flatnonzero(occ):
        if seen[start]:continue
        stack=[int(start)];seen[start]=True;comp=[];mask=0
        while stack:
            s=stack.pop();comp.append(s);r,c=divmod(s,L)
            if c==0:mask|=1
            if c==L-1:mask|=2
            if r==0:mask|=4
            if r==L-1:mask|=8
            for nb in (s-1,s+1,s-L,s+L):
                if 0<=nb<L*L and occ[nb] and not seen[nb] and not (nb==s-1 and c==0) and not (nb==s+1 and c==L-1):seen[nb]=True;stack.append(nb)
        if (mask&3)==3 or (mask&12)==12:return comp
    return []

def render(out):
    import matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation,PillowWriter
    rows=list(csv.DictReader((out/"spanning-curves.csv").open())); result=json.loads((out/"threshold-fit.json").read_text())
    fig,ax=plt.subplots(figsize=(8,5))
    for L in SIZES:ax.plot([float(r["p"]) for r in rows],[float(r[f"L{L}"]) for r in rows],label=f"L={L}")
    ax.axvline(PAPER,color="black",ls="--",lw=1,label="published pc");ax.set(xlabel="occupation probability p",ylabel="spanning probability",title="Square-lattice site-percolation transition");ax.legend();fig.tight_layout();fig.savefig(out/"spanning-probability.png",dpi=160);plt.close(fig)
    x=np.array([L**(-.75) for L in SIZES]);y=np.array([result["p50"][str(L)] for L in SIZES]);coef=np.polyfit(x,y,1)
    fig,ax=plt.subplots(figsize=(7,5));ax.scatter(x,y,color="black");xx=np.linspace(0,x.max()*1.05,100);ax.plot(xx,np.polyval(coef,xx));ax.axhline(PAPER,ls="--",color="gray");ax.set(xlabel=r"$L^{-3/4}$",ylabel=r"$p_{50}(L)$",title=f"Finite-size threshold fit: pc={result['pc']:.6f}");fig.tight_layout();fig.savefig(out/"threshold-extrapolation.png",dpi=160);plt.close(fig)
    L=128;rng=rng_for(L,0);order=rng.permutation(L*L);fractions=np.linspace(.45,.75,61);snapshots=[]
    for p in fractions:
        occ=np.zeros(L*L,bool);occ[order[:round(p*L*L)]]=True;arr=occ.reshape(L,L).astype(np.uint8);comp=spanning_component(occ,L);arr.flat[comp]=2;snapshots.append(arr)
    fig,ax=plt.subplots(figsize=(6,6));im=ax.imshow(snapshots[0],vmin=0,vmax=2,cmap=matplotlib.colors.ListedColormap(["white","#777777","#d62728"]),interpolation="nearest");title=ax.set_title("");ax.axis("off")
    def update(i):im.set_data(snapshots[i]);title.set_text(f"L=128, p={fractions[i]:.3f}"+(" — spanning cluster in red" if np.any(snapshots[i]==2) else ""));return im,title
    ani=FuncAnimation(fig,update,frames=len(snapshots),blit=False);ani.save(out/"cluster-growth.gif",writer=PillowWriter(fps=10));update(int(np.argmin(abs(fractions-.593))));fig.tight_layout();fig.savefig(out/"cluster-growth.png",dpi=160);plt.close(fig)

def validate(out,reference=None):
    required=["input.json","provenance.json","threshold-fit.json","spanning-curves.csv","connectivity-audit.json","spanning-probability.png","threshold-extrapolation.png","cluster-growth.png","cluster-growth.gif"]+[f"shards/l{L:03d}-s{s}.npy" for L in SIZES for s in range(SHARDS)]
    missing=[p for p in required if not (out/p).is_file()]; checks={"missing":missing,"scientific_pass":json.loads((out/"threshold-fit.json").read_text())["passed"]}
    from PIL import Image
    gif=Image.open(out/"cluster-growth.gif");checks["gif_frames"]=gif.n_frames;checks["gif_multiframe"]=gif.n_frames>1
    hashes={p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in required};write_json(out/"checksums.json",hashes)
    if reference:
        ref={p:hashlib.sha256((reference/p).read_bytes()).hexdigest() for p in required};checks["reference_match"]=hashes==ref
    checks["passed"]=not missing and checks["scientific_pass"] and checks["gif_multiframe"] and checks.get("reference_match",True);write_json(out/"validation.json",checks)
    if not checks["passed"]:raise SystemExit("validation failed")

def main():
    p=argparse.ArgumentParser();p.add_argument("command",choices=["prepare","shard","aggregate","render","validate"]);p.add_argument("--output",required=True);p.add_argument("--size",type=int);p.add_argument("--shard",type=int);p.add_argument("--reference");a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if a.command=="prepare":prepare(out)
    elif a.command=="shard":shard(out,a.size,a.shard)
    elif a.command=="aggregate":aggregate(out)
    elif a.command=="render":render(out)
    else:validate(out,Path(a.reference) if a.reference else None)
if __name__=="__main__":main()
