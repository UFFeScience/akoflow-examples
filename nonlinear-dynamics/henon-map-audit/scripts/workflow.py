#!/usr/bin/env python3
import argparse,csv,gzip,hashlib,io,json,math
from pathlib import Path
import numpy as np

A=1.4; B=.3; BURN=10_000; STEPS=1_000_000
BRANCHES={"origin":(0.,0.),"x-offset":(.1,0.),"y-offset":(0.,.1),"xy-offset":(-.1,.1)}
GRIDS=((75,25),(150,50),(300,100),(600,200),(1200,400))
CHECKPOINTS=tuple(sorted(set(np.geomspace(10,STEPS,80,dtype=int).tolist())))

def dump(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def step(x,y): return 1+y-A*x*x,B*x
def grid_index(x,y,nx,ny): return min(nx-1,max(0,int((x+1.5)*nx/3))),min(ny-1,max(0,int((y+.5)*ny)))

def prepare(out):
 dump(out/"scenario.json",{"paper":"Michel Henon, A Two-dimensional Mapping with a Strange Attractor","doi":"10.1007/BF01608556","a":A,"b":B,"burn_in":BURN,"retained":STEPS,"initial_points":BRANCHES,"grids":GRIDS,"precision":"IEEE-754 binary64"})

def iterate(out,branch):
 x,y=BRANCHES[branch]
 for _ in range(BURN): x,y=step(x,y)
 q=np.eye(2,dtype=np.float64); sums=np.zeros(2,dtype=np.float64); occ=[np.zeros(nx*ny,dtype=np.uint8) for nx,ny in GRIDS]; samples=[]; conv=[]
 xmin=xmax=x; ymin=ymax=y
 for i in range(1,STEPS+1):
  j=np.array(((-2*A*x,1.),(B,0.)),dtype=np.float64); x,y=step(x,y)
  z=j@q; q0=z[:,0]; r0=np.linalg.norm(q0); q0/=r0; q1=z[:,1]-q0*np.dot(q0,z[:,1]); r1=np.linalg.norm(q1); q1/=r1; q=np.column_stack((q0,q1)); sums+=np.log((r0,r1))
  xmin=min(xmin,x); xmax=max(xmax,x); ymin=min(ymin,y); ymax=max(ymax,y)
  for grid,(nx,ny) in zip(occ,GRIDS): ix,iy=grid_index(x,y,nx,ny); grid[iy*nx+ix]=1
  if i%20==0: samples.append((i,x,y))
  if i in CHECKPOINTS: conv.append((i,sums[0]/i,sums[1]/i))
 d=out/branch; d.mkdir(exist_ok=True)
 np.savez_compressed(d/"occupancy.npz",**{f"g{nx}x{ny}":v.reshape(ny,nx) for v,(nx,ny) in zip(occ,GRIDS)})
 with (d/"samples.csv.gz").open("wb") as raw:
  with gzip.GzipFile(filename="samples.csv",mode="wb",fileobj=raw,mtime=0) as compressed:
   with io.TextIOWrapper(compressed,newline="") as f: w=csv.writer(f); w.writerow(("iteration","x","y")); w.writerows(samples)
 with (d/"convergence.csv").open("w",newline="") as f: w=csv.writer(f); w.writerow(("iteration","lambda1","lambda2")); w.writerows(conv)
 counts=[int(v.sum()) for v in occ]; xs=np.log(np.array([nx/3 for nx,_ in GRIDS])); slope=float(np.polyfit(xs,np.log(counts),1)[0]); l1,l2=(sums/STEPS).tolist()
 dump(d/"summary.json",{"branch":branch,"initial":BRANCHES[branch],"burn_in":BURN,"retained":STEPS,"finite":all(map(math.isfinite,(x,y,l1,l2))),"bounds":{"xmin":xmin,"xmax":xmax,"ymin":ymin,"ymax":ymax},"occupied_bins":counts,"occupancy_slope":slope,"lambda1":l1,"lambda2":l2,"lambda_sum_error":abs(l1+l2-math.log(abs(B))),"kaplan_yorke":1+l1/abs(l2),"sample_rows":len(samples)})

def aggregate(out):
 summaries={b:json.loads((out/b/"summary.json").read_text()) for b in BRANCHES}; grids={b:np.load(out/b/"occupancy.npz")["g600x200"].astype(bool) for b in BRANCHES}; jac={}
 names=list(BRANCHES)
 for i,a in enumerate(names):
  for b in names[i+1:]: jac[f"{a}:{b}"]=float(np.logical_and(grids[a],grids[b]).sum()/np.logical_or(grids[a],grids[b]).sum())
 dump(out/"aggregate.json",{"branches":summaries,"pairwise_jaccard":jac,"lambda1_span":max(v["lambda1"] for v in summaries.values())-min(v["lambda1"] for v in summaries.values()),"dimension_span":max(v["kaplan_yorke"] for v in summaries.values())-min(v["kaplan_yorke"] for v in summaries.values()),"occupancy_slope_span":max(v["occupancy_slope"] for v in summaries.values())-min(v["occupancy_slope"] for v in summaries.values())})

def render(out):
 import matplotlib.pyplot as plt
 from PIL import Image
 samples={}
 for b in BRANCHES:
  with gzip.open(out/b/"samples.csv.gz","rt") as f: samples[b]=np.loadtxt(f,delimiter=",",skiprows=1)
 fig,ax=plt.subplots(figsize=(9,6)); colors=("#111111","#555555","#888888","#bbbbbb")
 for (b,v),c in zip(samples.items(),colors): ax.scatter(v[:,1],v[:,2],s=.05,color=c,label=b,rasterized=True)
 ax.set(xlim=(-1.5,1.5),ylim=(-.5,.5),xlabel="x",ylabel="y",title="Classical Hénon attractor: four post-transient trajectories"); ax.legend(markerscale=20); fig.tight_layout(); fig.savefig(out/"henon-attractor.png",dpi=180); plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,5))
 for b,c in zip(BRANCHES,colors): v=np.loadtxt(out/b/"convergence.csv",delimiter=",",skiprows=1); ax.semilogx(v[:,0],v[:,1],color=c,label=b)
 ax.axhline(.41922,color="#222222",ls="--",label="published ≈0.41922"); ax.set(xlabel="retained iterations",ylabel="finite-time λ₁",title="Lyapunov exponent convergence"); ax.legend(); fig.tight_layout(); fig.savefig(out/"lyapunov-convergence.png",dpi=180); plt.close(fig)
 frames=[]; conv={b:np.loadtxt(out/b/"convergence.csv",delimiter=",",skiprows=1) for b in BRANCHES}
 for k in range(1,len(CHECKPOINTS)+1):
  fig,ax=plt.subplots(figsize=(7,4.5))
  for (b,v),c in zip(conv.items(),colors): ax.semilogx(v[:k,0],v[:k,1],color=c,label=b); ax.plot(v[k-1,0],v[k-1,1],"o",color=c,ms=3)
  ax.axhline(.41922,color="#222222",ls="--"); ax.set(xlim=(10,STEPS),ylim=(.38,.46),xlabel="retained iterations",ylabel="finite-time λ₁",title=f"Convergence through n={CHECKPOINTS[k-1]:,}"); fig.tight_layout(); fig.canvas.draw(); frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert("P")); plt.close(fig)
 frames[0].save(out/"lyapunov-convergence.gif",save_all=True,append_images=frames[1:],duration=90,loop=0)

def validate(out,reference=None):
 a=json.loads((out/"aggregate.json").read_text()); s=a["branches"]
 checks={"complete":set(s)==set(BRANCHES),"counts":all(v["retained"]==STEPS and v["sample_rows"]==50_000 for v in s.values()),"finite":all(v["finite"] for v in s.values()),"domain":all(v["bounds"]["xmin"]>=-1.5 and v["bounds"]["xmax"]<=1.5 and v["bounds"]["ymin"]>=-.5 and v["bounds"]["ymax"]<=.5 and v["bounds"]["xmin"]<0<v["bounds"]["xmax"] for v in s.values()),"multiscale":all(all(x<y for x,y in zip(v["occupied_bins"],v["occupied_bins"][1:])) and 1<v["occupancy_slope"]<2 for v in s.values()) and a["occupancy_slope_span"]<=.01,"spectrum":all(.414<=v["lambda1"]<=.424 and -1.628<=v["lambda2"]<=-1.618 for v in s.values()),"contraction":all(v["lambda_sum_error"]<=1e-10 for v in s.values()),"dimension":all(1.253<=v["kaplan_yorke"]<=1.263 for v in s.values()) and a["dimension_span"]<=.003,"lambda_span":a["lambda1_span"]<=.003,"jaccard":all(v>=.85 for v in a["pairwise_jaccard"].values()),"gallery":all((out/n).stat().st_size>1000 for n in ("henon-attractor.png","lyapunov-convergence.png","lyapunov-convergence.gif"))}
 stable=["scenario.json","aggregate.json","henon-attractor.png","lyapunov-convergence.png","lyapunov-convergence.gif"]+[f"{b}/{n}" for b in BRANCHES for n in ("summary.json","occupancy.npz","samples.csv.gz","convergence.csv")]
 if reference: checks["repeat"]={n:(out/n).read_bytes()==(reference/n).read_bytes() for n in stable}
 passed=all(v if isinstance(v,bool) else all(v.values()) for v in checks.values()); dump(out/"validation.json",{"passed":passed,"checks":checks,"scientific_scope":"finite-precision numerical audit, not a proof of a strange attractor"}); files=[p for p in out.rglob("*") if p.is_file() and p.name!="manifest.json"]; dump(out/"manifest.json",{"files":[{"path":str(p.relative_to(out)),"bytes":p.stat().st_size,"sha256":digest(p)} for p in sorted(files)]})
 if not passed: raise SystemExit(1)

def main():
 p=argparse.ArgumentParser(); p.add_argument("mode",choices=("prepare","iterate","aggregate","render","validate")); p.add_argument("--output",required=True); p.add_argument("--branch",choices=BRANCHES); p.add_argument("--reference"); a=p.parse_args(); out=Path(a.output); out.mkdir(parents=True,exist_ok=True); {"prepare":lambda:prepare(out),"iterate":lambda:iterate(out,a.branch),"aggregate":lambda:aggregate(out),"render":lambda:render(out),"validate":lambda:validate(out,Path(a.reference) if a.reference else None)}[a.mode]()
if __name__=="__main__": main()
