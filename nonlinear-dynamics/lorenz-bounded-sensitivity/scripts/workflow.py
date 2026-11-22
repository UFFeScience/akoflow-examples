#!/usr/bin/env python3
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
BRANCHES={"reference":(1.,1.,1.),"perturb-x":(1.+1e-8,1.,1.),"perturb-y":(1.,1.+1e-8,1.),"perturb-z":(1.,1.,1.+1e-8)}
EXPECTED={"reference":"304c89e0a5c2480242873ac136df402f896b1e4c2686e4968f0e39043de7f87e","perturb-x":"bea2e6c60ac198737d53b2715192576e065f4f542bfe5716c0f137980d1d5512","perturb-y":"e6d484ca3d801efbe25cf127766492cf242ac1dbd522d5ecaf7af8cf146275dc","perturb-z":"c75e5d89ca87b8dfdd6a6761abb980b48c8058a225ddf4da07c3b712245984b7"}
DT=.001;STEPS=40000
def dump(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
def rhs(s):
 x,y,z=s;return np.array((10*(y-x),x*(28-z)-y,x*y-(8/3)*z),dtype=np.float64)
def rk4(s):
 k1=rhs(s);k2=rhs(s+DT*k1/2);k3=rhs(s+DT*k2/2);k4=rhs(s+DT*k3);return s+DT*(k1+2*k2+2*k3+k4)/6
def prepare(o):dump(o/"scenario.json",{"paper":"Lorenz 1963 Deterministic Nonperiodic Flow","doi":"10.1175/1520-0469(1963)020<0130:DNF>2.0.CO;2","sigma":10,"rho":28,"beta":8/3,"dt":DT,"steps":STEPS,"initial_states":BRANCHES})
def simulate(o,b):
 a=np.empty((STEPS+1,3),dtype="<f8");a[0]=BRANCHES[b]
 for i in range(STEPS):a[i+1]=rk4(a[i])
 d=o/b;d.mkdir(exist_ok=True);np.save(d/"trajectory.npy",a,allow_pickle=False)
 with (d/"trajectory.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(("t","x","y","z"));w.writerows((i*DT,*v) for i,v in enumerate(a))
 dump(d/"summary.json",{"branch":b,"rows":len(a),"max_abs":float(np.abs(a).max()),"sha256":hashlib.sha256(a.tobytes()).hexdigest(),"final":a[-1].tolist()})
def aggregate(o):
 a={b:np.load(o/b/"trajectory.npy") for b in BRANCHES};r=a["reference"];m={};seps={b:np.linalg.norm(a[b]-r,axis=1) for b in list(BRANCHES)[1:]}
 with (o/"separation.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(("t","perturb_x","perturb_y","perturb_z"));w.writerows((i*DT,*(seps[b][i] for b in list(BRANCHES)[1:])) for i in range(STEPS+1))
 for b,s in seps.items():m[b]={"crossings":{str(q):float(np.argmax(s>=q)*DT) for q in (1e-6,1e-4,1e-2,1.,10.)},"final":float(s[-1]),"maximum":float(s.max())}
 dump(o/"metrics.json",m)
def render(o):
 import matplotlib.pyplot as plt
 from PIL import Image
 a={b:np.load(o/b/"trajectory.npy") for b in BRANCHES};colors=("#151515","#555555","#888888","#bbbbbb")
 fig=plt.figure(figsize=(9,7));ax=fig.add_subplot(projection="3d")
 for (b,v),c in zip(a.items(),colors):ax.plot(v[:,0],v[:,1],v[:,2],lw=.55,color=c,label=b)
 ax.set(xlabel="x",ylabel="y",zlabel="z",title="Lorenz-1963 bounded trajectories");ax.legend();fig.tight_layout();fig.savefig(o/"lorenz-attractor.png",dpi=150);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,5));r=a["reference"];t=np.arange(STEPS+1)*DT
 for (b,v),c in zip(list(a.items())[1:],colors[1:]):ax.semilogy(t,np.maximum(np.linalg.norm(v-r,axis=1),1e-16),color=c,label=b)
 ax.axhline(1,color="#151515",ls="--");ax.set(xlabel="time",ylabel="Euclidean separation",title="Sensitive dependence on initial state");ax.legend();fig.tight_layout();fig.savefig(o/"sensitivity.png",dpi=150);plt.close(fig)
 frames=[]
 for i in np.linspace(0,STEPS,60,dtype=int):
  fig,ax=plt.subplots(figsize=(6,5))
  for (_,v),c in zip(a.items(),colors):ax.plot(v[:i+1,0],v[:i+1,2],color=c,lw=.7);ax.plot(v[i,0],v[i,2],"o",color=c,ms=3)
  ax.set(xlim=(-22,22),ylim=(0,50),xlabel="x",ylabel="z",title=f"Lorenz divergence, t={i*DT:.1f}");fig.tight_layout();fig.canvas.draw();frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert("P"));plt.close(fig)
 frames[0].save(o/"lorenz-divergence.gif",save_all=True,append_images=frames[1:],duration=100,loop=0)
def validate(o,ref=None):
 summ={b:json.loads((o/b/"summary.json").read_text()) for b in BRANCHES};met=json.loads((o/"metrics.json").read_text());checks={"rows":{b:summ[b]["rows"]==40001 for b in BRANCHES},"hashes":{b:summ[b]["sha256"]==EXPECTED[b] for b in BRANCHES},"bounded":{b:summ[b]["max_abs"]<50 for b in BRANCHES},"unit_crossing":{b:28<=met[b]["crossings"]["1.0"]<=32 for b in met},"ten_by_34":{b:met[b]["crossings"]["10.0"]<=34 for b in met},"max_separation":{b:met[b]["maximum"]>=40 for b in met},"gallery":all((o/x).stat().st_size>1000 for x in ("lorenz-attractor.png","sensitivity.png","lorenz-divergence.gif"))}
 if ref:checks["repeat"]={b:(o/b/"trajectory.npy").read_bytes()==(ref/b/"trajectory.npy").read_bytes() for b in BRANCHES}
 ok=all(v if isinstance(v,bool) else all(v.values()) for v in checks.values());dump(o/"validation.json",{"passed":ok,"checks":checks,"metrics":met,"expected_hashes":EXPECTED});files=[p for p in o.rglob("*") if p.is_file() and p.name!="manifest.json"];dump(o/"manifest.json",{"files":[{"path":str(p.relative_to(o)),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]})
 if not ok:raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument("mode",choices=("prepare","simulate","aggregate","render","validate"));p.add_argument("--output",required=True);p.add_argument("--branch",choices=BRANCHES);p.add_argument("--reference");a=p.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=True);{"prepare":lambda:prepare(o),"simulate":lambda:simulate(o,a.branch),"aggregate":lambda:aggregate(o),"render":lambda:render(o),"validate":lambda:validate(o,Path(a.reference) if a.reference else None)}[a.mode]()
if __name__=="__main__":main()
