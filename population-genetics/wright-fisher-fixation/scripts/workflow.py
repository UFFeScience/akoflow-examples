#!/usr/bin/env python3
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np

VERSION="community-wright-fisher-fixation-v1"; SEED_VERSION="kimura-wright-fisher-v1"
K=200; PS=("0.05","0.10","0.25","0.50","0.75"); N=5000; Z=2.5758293035489004
def dump(path,obj): Path(path).write_text(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n")
def seed(p,s,r):
 key=f"{SEED_VERSION}|p0={p}|shard={s}|replicate={r}"
 return int.from_bytes(hashlib.sha256(key.encode()).digest(),"little")
def prepare(out):
 out.mkdir(parents=True,exist_ok=True)
 rows=[{"p0":float(p),"initial_count":round(K*float(p)),"exact_fixation":float(p)} for p in PS]
 dump(out/"scenario-manifest.json",{"workflow_version":VERSION,"seed_version":SEED_VERSION,"population_gene_copies":K,"frequencies":rows,"shards":4,"replicates_per_shard":N,"bit_generator":"PCG64DXSM"})
 with (out/"reference-fixation.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
def simulate(out,p,s):
 outcomes=np.empty(N,np.uint8); generations=np.empty(N,np.uint32); traces={}
 for r in range(N):
  rng=np.random.Generator(np.random.PCG64DXSM(seed(p,s,r))); x=round(K*float(p)); g=0; trace=[x]
  while x not in (0,K):
   x=int(rng.binomial(K,x/K)); g+=1
   if r<3: trace.append(x)
   if g>100000: raise RuntimeError("absorption safety cap")
  outcomes[r]=x==K; generations[r]=g
  if r<3: traces[str(r)]=trace
 np.savez(out/f"shard-p{p.replace('.','')}-{s}.npz",outcomes=outcomes,generations=generations)
 dump(out/f"traces-p{p.replace('.','')}-{s}.json",traces)
def wilson(k,n):
 p=k/n; z2=Z*Z; c=(p+z2/(2*n))/(1+z2/n); h=Z*math.sqrt(p*(1-p)/n+z2/(4*n*n))/(1+z2/n); return [c-h,c+h]
def aggregate(out,p):
 aa=[]; gg=[]
 for s in range(4):
  z=np.load(out/f"shard-p{p.replace('.','')}-{s}.npz"); aa.append(z["outcomes"]); gg.append(z["generations"])
 a=np.concatenate(aa); g=np.concatenate(gg); k=int(a.sum()); q=float(p); interval=wilson(k,len(a)); tol=max(.012,4*math.sqrt(q*(1-q)/len(a)))
 survival=np.bincount(g,minlength=int(g.max())+1)[::-1].cumsum()[::-1]/len(g)
 np.save(out/f"survival-p{p.replace('.','')}.npy",survival)
 dump(out/f"summary-p{p.replace('.','')}.json",{"p0":q,"fixations":k,"losses":int(len(a)-k),"estimate":k/len(a),"absolute_error":abs(k/len(a)-q),"tolerance":tol,"wilson_99":interval,"median_generation":float(np.median(g)),"q99_generation":float(np.quantile(g,.99)),"max_generation":int(g.max()),"pass":abs(k/len(a)-q)<=tol and interval[0]<=q<=interval[1]})
def render(out):
 import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
 rows=[json.loads((out/f"summary-p{p.replace('.','')}.json").read_text()) for p in PS]
 x=np.array([r["p0"] for r in rows]); y=np.array([r["estimate"] for r in rows]); lo=np.array([r["wilson_99"][0] for r in rows]); hi=np.array([r["wilson_99"][1] for r in rows])
 fig,ax=plt.subplots(figsize=(7,5)); ax.plot([0,1],[0,1],"k--",label="exact u(p₀)=p₀"); ax.errorbar(x,y,yerr=[y-lo,hi-y],fmt="o",label="20,000 replicates, 99% Wilson"); ax.set(xlabel="Initial allele frequency p₀",ylabel="Eventual fixation probability",title="Neutral Wright–Fisher fixation law"); ax.legend(); fig.tight_layout(); fig.savefig(out/"fixation-probability.png",dpi=180); plt.close(fig)
 distributions=[]
 for p in PS:
  distributions.append(np.concatenate([np.load(out/f"shard-p{p.replace('.','')}-{s}.npz")["generations"] for s in range(4)]))
 fig,ax=plt.subplots(figsize=(7,5)); ax.boxplot(distributions,tick_labels=PS,showfliers=False,whis=(1,99)); ax.set(xlabel="p₀",ylabel="Absorption generation",title="Absorption-time distributions (1st–99th percentiles)"); fig.tight_layout(); fig.savefig(out/"absorption-times.png",dpi=180); plt.close(fig)
 from PIL import Image,ImageDraw
 traces=[]
 for p in PS: traces.append(json.loads((out/f"traces-p{p.replace('.','')}-0.json").read_text())["0"])
 frames=[]
 for t in range(0,max(map(len,traces)),max(1,max(map(len,traces))//80)):
  im=Image.new("RGB",(720,420),"white"); d=ImageDraw.Draw(im); d.text((20,15),f"Neutral allele drift — generation {t}",fill="black")
  for i,tr in enumerate(traces):
   pts=[]
   for j in range(min(t+1,len(tr))): pts.append((40+j*650/max(1,max(map(len,traces))-1),370-tr[j]*320/K))
   if len(pts)>1:d.line(pts,fill=(30+i*40,80,180-i*20),width=3)
  frames.append(im)
 frames[0].save(out/"allele-drift.gif",save_all=True,append_images=frames[1:],duration=90,loop=0)
def validate(out):
 rows=[json.loads((out/f"summary-p{p.replace('.','')}.json").read_text()) for p in PS]; q25,q75=rows[2],rows[4]
 sym1=abs(q25["estimate"]-(1-q75["estimate"])); sym2=abs(q25["median_generation"]-q75["median_generation"])/max(q25["median_generation"],q75["median_generation"])
 files=["scenario-manifest.json","reference-fixation.csv","fixation-probability.png","absorption-times.png","allele-drift.gif"]+[f"summary-p{p.replace('.','')}.json" for p in PS]
 hashes={f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in files}; ok=all(r["pass"] for r in rows) and sym1<=.02 and sym2<=.15
 dump(out/"validation.json",{"workflow_version":VERSION,"overall_pass":ok,"frequency_results":rows,"symmetry":{"fixation_loss_difference":sym1,"median_relative_difference":sym2,"pass":sym1<=.02 and sym2<=.15},"checksums":hashes,"limitations":["neutral haploid finite-population slice","simulation generations are not laboratory time","no selection, mutation, migration, or diploid genotype sampling"]})
 if not ok: raise SystemExit(1)
def main():
 a=argparse.ArgumentParser(); a.add_argument("mode",choices=["prepare","simulate","aggregate","render","validate"]); a.add_argument("--output",default="."); a.add_argument("--p0"); a.add_argument("--shard",type=int); x=a.parse_args(); out=Path(x.output)
 {"prepare":lambda:prepare(out),"simulate":lambda:simulate(out,x.p0,x.shard),"aggregate":lambda:aggregate(out,x.p0),"render":lambda:render(out),"validate":lambda:validate(out)}[x.mode]()
if __name__=="__main__": main()
