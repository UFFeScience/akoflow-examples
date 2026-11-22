"""Deterministic finite-lattice reproduction of Yang's 2D Ising magnetization curve."""
import argparse, csv, hashlib, json, math, platform
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numba, numpy as np
from numba import njit

VERSION="community-ising-yang-v1"
TC=2.269185314213022
LOW_T=(1.50,1.75,2.00,2.10,2.20)
CRIT_T=tuple(round(2.16+0.02*i,2) for i in range(12))
SIZES=(32,64,96);REPLICATES=4;BURN=500;MEASURE=2000;SHARDS=8

def dump(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def load(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def exact(t):return 0.0 if t>=TC else (1.0-math.sinh(2.0/t)**-4.0)**0.125
def seed_for(L,t,rep):return int.from_bytes(hashlib.sha256(f"{VERSION}|L={L}|T={t:.2f}|replicate={rep}".encode()).digest()[:8],"big")
def specs():
 return [(L,t,r) for L in SIZES for t in sorted(set(CRIT_T+(LOW_T if L==96 else ()))) for r in range(REPLICATES)]
def branch_id(L,t,r):return f"L{L}-T{t:.2f}-R{r}"

@njit(cache=True,nogil=True)
def simulate(L,t,rng,burn,measure,keep_snapshots):
 n=L*L;spins=np.ones(n,dtype=np.int8);marks=np.zeros(n,dtype=np.int32)
 stack=np.empty(n,dtype=np.int32);cluster=np.empty(n,dtype=np.int32)
 values=np.empty((measure,4),dtype=np.float64);snapshots=np.empty((10,n),dtype=np.int8)
 p_add=1.0-math.exp(-2.0/t);sweeps=flipped=generation=sample=snapshot=0
 while sweeps<burn+measure:
  generation+=1;root=int(rng.integers(0,n));spin=spins[root];marks[root]=generation;stack[0]=root;top=1;count=0
  while top:
   top-=1;site=stack[top];cluster[count]=site;count+=1;row=site//L;col=site-row*L
   neighbors=(row*L+(col+1)%L,row*L+(col-1+L)%L,((row+1)%L)*L+col,((row-1+L)%L)*L+col)
   for neighbor in neighbors:
    if marks[neighbor]!=generation and spins[neighbor]==spin and rng.random()<p_add:
     marks[neighbor]=generation;stack[top]=neighbor;top+=1
  for j in range(count):spins[cluster[j]]=-spin
  flipped+=count
  if flipped>=n:
   flipped-=n;sweeps+=1
   if sweeps>burn:
    m=np.sum(spins)/n;e=0.0
    for row in range(L):
     base=row*L;down=((row+1)%L)*L
     for col in range(L):e-=spins[base+col]*(spins[base+(col+1)%L]+spins[down+col])
    e/=n;values[sample,0]=abs(m);values[sample,1]=m*m;values[sample,2]=m*m*m*m;values[sample,3]=e
    if keep_snapshots and sample%200==199:snapshots[snapshot,:]=spins;snapshot+=1
    sample+=1
 return values,snapshots[:snapshot]

def prepare(output):
 output=Path(output);rows=[]
 for index,(L,t,r) in enumerate(specs()):rows.append({"id":branch_id(L,t,r),"L":L,"temperature":t,"replicate":r,"seed":seed_for(L,t,r),"shard":index%SHARDS})
 assert len(rows)==160 and len({r["id"] for r in rows})==160
 dump(output/"scenario-manifest.json",{"version":VERSION,"model":"zero-field periodic square-lattice Ising model","J":1,"kB":1,"algorithm":"Wolff single-cluster","criticalTemperature":TC,"burnSweepEquivalents":BURN,"measurementSweepEquivalents":MEASURE,"blocks":20,"rng":"NumPy PCG64DXSM","branches":rows,"versions":{"python":platform.python_version(),"numpy":np.__version__,"numba":numba.__version__,"matplotlib":matplotlib.__version__}})
 with (output/"reference-curve.csv").open("w",newline="") as handle:
  writer=csv.writer(handle,lineterminator="\n");writer.writerow(("temperature","exact_magnetization"))
  for t in sorted(set(LOW_T+CRIT_T)):writer.writerow((f"{t:.2f}",format(exact(t),".17g")))

def sample_shard(shard,output):
 output=Path(output);manifest=load(output/"scenario-manifest.json");rows=[]
 for spec in manifest["branches"]:
  if spec["shard"]!=shard:continue
  seed=spec["seed"];rng=np.random.Generator(np.random.PCG64DXSM(np.uint64(seed)))
  keep=spec["L"]==96 and spec["replicate"]==0 and spec["temperature"] in (1.50,2.28,2.38)
  values,snapshots=simulate(spec["L"],spec["temperature"],rng,BURN,MEASURE,keep)
  target=output/"branches"/spec["id"];target.mkdir(parents=True,exist_ok=True);np.save(target/"measurements.npy",values,allow_pickle=False)
  if keep:np.save(target/"snapshots.npy",snapshots,allow_pickle=False)
  blocks=values[:,0].reshape(20,-1).mean(axis=1)
  rows.append({**spec,"samples":len(values),"meanAbsM":float(values[:,0].mean()),"meanM2":float(values[:,1].mean()),"meanM4":float(values[:,2].mean()),"meanEnergy":float(values[:,3].mean()),"minimumEnergy":float(values[:,3].min()),"maximumEnergy":float(values[:,3].max()),"blockMeans":blocks.tolist(),"measurementsSha256":sha(target/"measurements.npy")})
 dump(output/"branches"/f"shard-{shard}.json",rows)

def crossing(first,second):
 differences=np.asarray(first)-np.asarray(second);candidates=[]
 for i in range(len(CRIT_T)-1):
  if differences[i]==0:candidates.append(CRIT_T[i])
  elif differences[i]*differences[i+1]<0:
   candidates.append(CRIT_T[i]-differences[i]*(CRIT_T[i+1]-CRIT_T[i])/(differences[i+1]-differences[i]))
 return min(candidates,key=lambda value:abs(value-TC)) if candidates else None

def aggregate(output):
 output=Path(output);rows=[]
 for shard in range(SHARDS):rows.extend(load(output/"branches"/f"shard-{shard}.json"))
 rows.sort(key=lambda r:(r["L"],r["temperature"],r["replicate"]));pooled={}
 for L,t,_r in specs():
  key=(L,t)
  if key in pooled:continue
  group=[r for r in rows if r["L"]==L and r["temperature"]==t];blocks=np.asarray([b for r in group for b in r["blockMeans"]])
  m2=np.mean([r["meanM2"] for r in group]);m4=np.mean([r["meanM4"] for r in group])
  pooled[key]={"L":L,"temperature":t,"meanAbsM":float(np.mean([r["meanAbsM"] for r in group])),"standardError":float(blocks.std(ddof=1)/math.sqrt(len(blocks))),"meanEnergy":float(np.mean([r["meanEnergy"] for r in group])),"binder":float(1.0-m4/(3.0*m2*m2)),"susceptibility":float(L*L*(m2-np.mean([r["meanAbsM"] for r in group])**2)/t)}
 crossings=[crossing([pooled[(32,t)]["binder"] for t in CRIT_T],[pooled[(64,t)]["binder"] for t in CRIT_T]),crossing([pooled[(64,t)]["binder"] for t in CRIT_T],[pooled[(96,t)]["binder"] for t in CRIT_T])]
 dump(output/"aggregate.json",{"branches":rows,"pooled":[pooled[k] for k in sorted(pooled)],"binderCrossings":{"L32-L64":crossings[0],"L64-L96":crossings[1]},"crossingMean":float(np.mean(crossings))})
 with (output/"pooled-observables.csv").open("w",newline="") as handle:
  writer=csv.DictWriter(handle,fieldnames=("L","temperature","meanAbsM","standardError","meanEnergy","binder","susceptibility"),lineterminator="\n");writer.writeheader();writer.writerows([pooled[k] for k in sorted(pooled)])

def render(output):
 output=Path(output);aggregate=load(output/"aggregate.json");rows=aggregate["pooled"]
 fig,axes=plt.subplots(1,2,figsize=(12,5));grid=np.linspace(1.45,TC,300);axes[0].plot(grid,[exact(t) for t in grid],"k-",label="Yang exact")
 for L in SIZES:
  data=[r for r in rows if r["L"]==L];axes[0].errorbar([r["temperature"] for r in data],[r["meanAbsM"] for r in data],yerr=[r["standardError"] for r in data],marker="o",linestyle="none",label=f"L={L}")
  critical=[r for r in data if r["temperature"] in CRIT_T];axes[1].plot([r["temperature"] for r in critical],[r["binder"] for r in critical],"o-",label=f"L={L}")
 axes[0].axvline(TC,color="gray",ls="--");axes[0].set(xlabel="Temperature T",ylabel="|m|",title="Finite lattice vs Yang magnetization");axes[0].legend()
 axes[1].axvline(TC,color="gray",ls="--");axes[1].set(xlabel="Temperature T",ylabel="Binder cumulant U4",title="Finite-size Binder crossings");axes[1].legend();fig.tight_layout();fig.savefig(output/"ising-phase-transition.png",dpi=180);plt.close(fig)
 configs=[]
 for t in (1.50,2.28,2.38):configs.append((t,np.load(output/"branches"/branch_id(96,t,0)/"snapshots.npy",allow_pickle=False)))
 fig,axes=plt.subplots(1,3,figsize=(10,3.6))
 def update(frame):
  for axis,(t,states) in zip(axes,configs):axis.clear();axis.imshow(states[frame].reshape(96,96),cmap="binary",vmin=-1,vmax=1,interpolation="nearest");axis.set_title(f"T={t:.2f}, sample {(frame+1)*200}");axis.axis("off")
 FuncAnimation(fig,update,frames=10,interval=300).save(output/"spin-configurations.gif",writer=PillowWriter(fps=3));plt.close(fig)

def validate(output,reference=None):
 output=Path(output);aggregate=load(output/"aggregate.json");branches=aggregate["branches"];pooled={(r["L"],r["temperature"]):r for r in aggregate["pooled"]};crossings=list(aggregate["binderCrossings"].values())
 residuals={f"T{t:.2f}":{"observed":pooled[(96,t)]["meanAbsM"],"exact":exact(t),"absoluteError":abs(pooled[(96,t)]["meanAbsM"]-exact(t)),"limit":max(0.03,3*pooled[(96,t)]["standardError"])} for t in LOW_T}
 checks={"exactTc":abs(TC-2/math.log(1+math.sqrt(2)))<=1e-14,"completeUniqueBranches":len(branches)==len({r["id"] for r in branches})==160,"sampleCounts":all(r["samples"]==MEASURE for r in branches),"physicalBounds":all(-2<=r["minimumEnergy"]<=r["maximumEnergy"]<=2 and 0<=r["meanAbsM"]<=1 for r in branches),"magnetizationResiduals":all(r["absoluteError"]<=r["limit"] for r in residuals.values()),"orderedVsHot":pooled[(96,1.50)]["meanAbsM"]>pooled[(96,2.38)]["meanAbsM"],"crossingsExist":all(c is not None and 2.16<=c<=2.38 for c in crossings),"crossingMean":abs(float(np.mean(crossings))-TC)<=0.05,"crossingAgreement":abs(crossings[0]-crossings[1])<=0.08}
 required=("scenario-manifest.json","reference-curve.csv","aggregate.json","pooled-observables.csv","ising-phase-transition.png","spin-configurations.gif");checks["requiredFiles"]=all((output/x).is_file() and (output/x).stat().st_size for x in required)
 if reference:
  reference=Path(reference);checks["repeatMeasurements"]=all((output/"branches"/r["id"]/"measurements.npy").read_bytes()==(reference/"branches"/r["id"]/"measurements.npy").read_bytes() for r in branches);checks["repeatAggregate"]=(output/"aggregate.json").read_bytes()==(reference/"aggregate.json").read_bytes()
 inventory={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob("*")) if p.is_file() and p.name not in ("validation.json","manifest.json")};report={"passed":all(checks.values()),"checks":checks,"criticalTemperature":TC,"binderCrossings":aggregate["binderCrossings"],"magnetizationResiduals":residuals,"inventory":inventory};dump(output/"validation.json",report);dump(output/"manifest.json",{"files":inventory,"validationPassed":report["passed"]})
 if not report["passed"]:raise SystemExit(json.dumps(report,indent=2))

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("stage",choices=("prepare","sample","aggregate","render","validate"));p.add_argument("--output",required=True);p.add_argument("--shard",type=int,choices=range(SHARDS));p.add_argument("--reference");a=p.parse_args();{"prepare":lambda:prepare(a.output),"sample":lambda:sample_shard(a.shard,a.output),"aggregate":lambda:aggregate(a.output),"render":lambda:render(a.output),"validate":lambda:validate(a.output,a.reference)}[a.stage]()
