"""Deterministic Robertson stiff-kinetics solver agreement workflow."""
import argparse, csv, hashlib, json, platform
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np
import scipy
from scipy.integrate import solve_ivp

METHODS=("Radau","BDF","LSODA")
RTOL=1e-10
ATOL=np.array((1e-12,1e-16,1e-12))
TIMES=np.concatenate(([0.0],4.0*10.0**np.arange(-1,11)))
REFERENCES={"y3_001":0.264019,"y1_0001":2.07951e7}

def dump(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def load(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rhs(_t,y):
 y1,y2,y3=y;return (-0.04*y1+1e4*y2*y3,0.04*y1-1e4*y2*y3-3e7*y2*y2,3e7*y2*y2)
def jac(_t,y):
 _y1,y2,y3=y
 return np.array(((-0.04,1e4*y3,1e4*y2),(0.04,-1e4*y3-6e7*y2,-1e4*y2),(0.0,6e7*y2,0.0)))
def event_y3(_t,y):return y[2]-0.01
def event_y1(_t,y):return y[0]-1e-4
event_y3.direction=1;event_y3.terminal=False;event_y1.direction=-1;event_y1.terminal=False

def prepare(output):
 output=Path(output);np.save(output/"evaluation-times.npy",TIMES,allow_pickle=False)
 dump(output/"scenario.json",{"model":"Robertson autocatalytic kinetics","equations":["dy1/dt=-0.04*y1+1e4*y2*y3","dy2/dt=0.04*y1-1e4*y2*y3-3e7*y2^2","dy3/dt=3e7*y2^2"],"initialState":[1,0,0],"interval":[0,4e10],"evaluationTimes":TIMES.tolist(),"jacobian":"exact analytic","methods":METHODS,"rtol":RTOL,"atol":ATOL.tolist(),"events":{"y3_001":{"value":0.01,"direction":"up","reference":REFERENCES["y3_001"]},"y1_0001":{"value":1e-4,"direction":"down","reference":REFERENCES["y1_0001"]}},"versions":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,"matplotlib":matplotlib.__version__}})

def solve(method,output):
 output=Path(output);times=np.load(output/"evaluation-times.npy",allow_pickle=False)
 sol=solve_ivp(rhs,(0,4e10),(1,0,0),method=method,t_eval=times,rtol=RTOL,atol=ATOL,jac=jac,events=(event_y3,event_y1))
 if not sol.success:raise RuntimeError(sol.message)
 branch=output/"branches"/method.lower();branch.mkdir(parents=True,exist_ok=True)
 np.savez(branch/"trajectory.npz",time=sol.t,concentrations=sol.y)
 metrics={"method":method,"success":bool(sol.success),"events":{"y3_001":[float(x) for x in sol.t_events[0]],"y1_0001":[float(x) for x in sol.t_events[1]]},"final":sol.y[:,-1].tolist(),"minimumConcentration":float(sol.y.min()),"maximumConservationError":float(np.max(np.abs(sol.y.sum(axis=0)-1))),"nfev":int(sol.nfev),"njev":int(sol.njev),"nlu":int(sol.nlu),"arraySha256":sha(branch/"trajectory.npz")}
 dump(branch/"metrics.json",metrics)

def aggregate(output):
 output=Path(output);metrics={m:load(output/"branches"/m.lower()/"metrics.json") for m in METHODS};arrays={m:np.load(output/"branches"/m.lower()/"trajectory.npz",allow_pickle=False)["concentrations"] for m in METHODS}
 pairs={};maximum=0.0
 for i,a in enumerate(METHODS):
  for b in METHODS[i+1:]:
   value=float(np.max(np.abs(arrays[a][:,-1]-arrays[b][:,-1])));pairs[f"{a}-{b}"]=value;maximum=max(maximum,value)
 events={m:{k:v[0] for k,v in metrics[m]["events"].items()} for m in METHODS}
 with (output/"solver-comparison.csv").open("w",newline="") as handle:
  writer=csv.writer(handle,lineterminator="\n");writer.writerow(("method","y3=0.01 time","y1=1e-4 time","final y1","final y2","final y3","max conservation error","nfev","njev","nlu"))
  for m in METHODS:writer.writerow((m,events[m]["y3_001"],events[m]["y1_0001"],*metrics[m]["final"],metrics[m]["maximumConservationError"],metrics[m]["nfev"],metrics[m]["njev"],metrics[m]["nlu"]))
 dump(output/"events.json",events);dump(output/"comparison.json",{"metrics":metrics,"events":events,"finalPairwiseMaximums":pairs,"maximumFinalPairwiseDifference":maximum})

def render(output):
 output=Path(output);arrays={m:np.load(output/"branches"/m.lower()/"trajectory.npz",allow_pickle=False) for m in METHODS};times=arrays["Radau"]["time"]
 fig,axes=plt.subplots(1,2,figsize=(12,5))
 for j,label in enumerate(("y1","y2","y3")):
  axes[0].plot(times[1:],arrays["Radau"]["concentrations"][j,1:],marker="o",label=label)
 axes[0].set_xscale("log");axes[0].set_yscale("log");axes[0].set(xlabel="model time",ylabel="concentration",title="Robertson kinetics across eleven decades");axes[0].legend()
 reference=arrays["Radau"]["concentrations"]
 for m in METHODS[1:]:axes[1].plot(times[1:],np.max(np.abs(arrays[m]["concentrations"][:,1:]-reference[:,1:]),axis=0),marker="o",label=f"{m} vs Radau")
 axes[1].set_xscale("log");axes[1].set_yscale("log");axes[1].set(xlabel="model time",ylabel="maximum absolute difference",title="Cross-solver residuals");axes[1].legend();fig.tight_layout();fig.savefig(output/"kinetics-logtime.png",dpi=180);plt.close(fig)
 fig,axis=plt.subplots(figsize=(7,5));y=reference
 def update(frame):
  axis.clear();end=max(2,frame+2);axis.plot(times[1:end],y[0,1:end],"o-",label="y1");axis.plot(times[1:end],y[1,1:end],"o-",label="y2");axis.plot(times[1:end],y[2,1:end],"o-",label="y3");axis.set_xscale("log");axis.set_yscale("log");axis.set(xlim=(0.4,4e10),ylim=(1e-13,2),xlabel="model time",ylabel="concentration",title="Robertson kinetics (model time)");axis.legend()
 FuncAnimation(fig,update,frames=len(times)-1,interval=300).save(output/"kinetics-logtime.gif",writer=PillowWriter(fps=3));plt.close(fig)

def validate(output,reference=None):
 output=Path(output);comparison=load(output/"comparison.json");metrics=comparison["metrics"];events=comparison["events"]
 checks={"threeSuccessfulSolvers":all(metrics[m]["success"] for m in METHODS),"oneEventEach":all(len(metrics[m]["events"][e])==1 for m in METHODS for e in REFERENCES),"eventTolerance":all(abs(events[m][e]-REFERENCES[e])/REFERENCES[e]<=2.5e-5 for m in METHODS for e in REFERENCES),"conservation":all(metrics[m]["maximumConservationError"]<=1e-10 for m in METHODS),"finiteNonnegative":all(np.isfinite(np.load(output/"branches"/m.lower()/"trajectory.npz")["concentrations"]).all() and metrics[m]["minimumConcentration"]>=-1e-12 for m in METHODS),"pairwiseFinal":comparison["maximumFinalPairwiseDifference"]<=2e-11,"finalY3":all(0.9999999<=metrics[m]["final"][2]<=1 for m in METHODS)}
 required=("scenario.json","evaluation-times.npy","solver-comparison.csv","events.json","comparison.json","kinetics-logtime.png","kinetics-logtime.gif");checks["requiredFiles"]=all((output/x).is_file() and (output/x).stat().st_size for x in required)
 if reference:
  reference=Path(reference);checks["repeatArrays"]=all((output/"branches"/m.lower()/"trajectory.npz").read_bytes()==(reference/"branches"/m.lower()/"trajectory.npz").read_bytes() for m in METHODS)
 inventory={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob("*")) if p.is_file() and p.name not in ("validation.json","manifest.json")};report={"passed":all(checks.values()),"checks":checks,"inventory":inventory};dump(output/"validation.json",report);dump(output/"manifest.json",{"files":inventory,"validationPassed":report["passed"]})
 if not report["passed"]:raise SystemExit(json.dumps(report,indent=2))

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("stage",choices=("prepare","solve","aggregate","render","validate"));p.add_argument("--output",required=True);p.add_argument("--method",choices=METHODS);p.add_argument("--reference");a=p.parse_args();{"prepare":lambda:prepare(a.output),"solve":lambda:solve(a.method,a.output),"aggregate":lambda:aggregate(a.output),"render":lambda:render(a.output),"validate":lambda:validate(a.output,a.reference)}[a.stage]()
