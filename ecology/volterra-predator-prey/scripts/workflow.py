"""Deterministic Volterra predator-prey invariant and cycle audit."""
import argparse, csv, hashlib, json, math, platform
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np
import scipy
from scipy.integrate import solve_ivp

ALPHA,BETA,DELTA,GAMMA=1.1,0.4,0.1,0.4
RTOL,ATOL,MAX_STEP=1e-11,1e-13,0.05
SCENARIOS={"moderate":(10.0,5.0,10.789),"prey-rich":(15.0,3.0,11.072),"predator-rich":(5.0,8.0,12.105)}
EQUILIBRIUM=(GAMMA/DELTA,ALPHA/BETA)

def dump(path,value):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def load(path): return json.loads(Path(path).read_text())
def sha256(path):
 digest=hashlib.sha256()
 with Path(path).open("rb") as handle:
  for block in iter(lambda:handle.read(1048576),b""):digest.update(block)
 return digest.hexdigest()
def rhs(_t,z):
 x,y=z; return ALPHA*x-BETA*x*y,DELTA*x*y-GAMMA*y
def invariant(x,y):return DELTA*x-GAMMA*np.log(x)+BETA*y-ALPHA*np.log(y)
def solve(name,output):
 x0,y0,period_reference=SCENARIOS[name]; direction=float(np.sign(rhs(0,(x0,y0))[0]))
 def crossing(t,z):return z[0]-x0
 crossing.direction=direction; crossing.terminal=False
 solution=solve_ivp(rhs,(0,100),(x0,y0),method="DOP853",rtol=RTOL,atol=ATOL,max_step=MAX_STEP,dense_output=True,events=crossing)
 if not solution.success:raise RuntimeError(solution.message)
 events=solution.t_events[0]; events=events[events>1e-8]; periods=np.diff(events); times=np.linspace(0,100,20001); values=solution.sol(times); x,y=values; h=invariant(x,y); h0=float(h[0])
 angles=np.unwrap(np.arctan2(y-EQUILIBRIUM[1],x-EQUILIBRIUM[0])); winding=float(abs(angles[-1]-angles[0])/(2*np.pi))
 prey_peaks=solution.t[np.where((solution.y[0,1:-1]>solution.y[0,:-2])&(solution.y[0,1:-1]>=solution.y[0,2:]))[0]+1]
 predator_peaks=solution.t[np.where((solution.y[1,1:-1]>solution.y[1,:-2])&(solution.y[1,1:-1]>=solution.y[1,2:]))[0]+1]
 offsets=[float(min(abs(predator_peaks-p))) for p in prey_peaks if len(predator_peaks)]
 rel_drift=float(np.max(np.abs(h-h0))/max(abs(h0),1e-15)); first=periods[:7]
 checks={"finite":bool(np.isfinite(values).all() and np.isfinite(periods).all()),"positive":bool(values.min()>0),"seven_cycles":len(first)==7,"invariant_drift":rel_drift<=1e-9,"period_stability":len(first)==7 and float(np.std(first)/np.mean(first))<=1e-6,"phase_offset":len(offsets)>=7 and min(offsets[:7])>=0.1 and max(offsets[:7])<float(np.mean(first)),"winding_agreement":abs(winding-len(events))<=1,"period_reference":len(first)==7 and abs(float(np.mean(first))-period_reference)<=0.01}
 result={"scenario":name,"initial_state":[x0,y0],"reference_period_neighborhood":period_reference,"event_times":[float(v) for v in events],"periods":[float(v) for v in periods],"mean_period":float(np.mean(first)),"period_cv":float(np.std(first)/np.mean(first)),"phase_offsets":offsets,"winding":winding,"invariant_initial":h0,"maximum_relative_invariant_drift":rel_drift,"minimum_population":float(values.min()),"checks":checks,"passed":all(checks.values())}
 branch=Path(output)/"branches"/name; branch.mkdir(parents=True,exist_ok=True)
 with (branch/"trajectory.csv").open("w",newline="") as handle:
  writer=csv.writer(handle,lineterminator="\n");writer.writerow(("time","prey","predator","invariant"));writer.writerows(zip(times,x,y,h))
 dump(branch/"metrics.json",result)
 if not result["passed"]:raise SystemExit(json.dumps(result,indent=2))
def prepare(output):
 dump(Path(output)/"scenario-manifest.json",{"model":"classical Volterra predator-prey","equations":["dx/dt=alpha*x-beta*x*y","dy/dt=delta*x*y-gamma*y"],"coefficients":{"alpha":ALPHA,"beta":BETA,"delta":DELTA,"gamma":GAMMA},"equilibrium":EQUILIBRIUM,"scenarios":{k:v[:2] for k,v in SCENARIOS.items()},"solver":{"method":"DOP853","rtol":RTOL,"atol":ATOL,"max_step":MAX_STEP,"interval":[0,100],"output_step":0.005},"versions":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,"matplotlib":matplotlib.__version__}})
def aggregate(output):
 output=Path(output);items=[load(output/"branches"/name/"metrics.json") for name in SCENARIOS];dump(output/"ensemble-metrics.json",{"passed":all(x["passed"] for x in items),"scenarios":items})
 with (output/"ensemble-metrics.csv").open("w",newline="") as handle:
  writer=csv.writer(handle,lineterminator="\n");writer.writerow(("scenario","mean_period","period_cv","relative_invariant_drift","winding"));writer.writerows((x["scenario"],x["mean_period"],x["period_cv"],x["maximum_relative_invariant_drift"],x["winding"]) for x in items)
def read_trajectory(path):
 data=np.genfromtxt(path,delimiter=",",names=True);return data
def render(output):
 output=Path(output); trajectories={name:read_trajectory(output/"branches"/name/"trajectory.csv") for name in SCENARIOS}; fig,axes=plt.subplots(1,2,figsize=(12,5))
 for name,data in trajectories.items():
  axes[0].plot(data["time"],data["prey"],label=f"{name} prey");axes[0].plot(data["time"],data["predator"],"--",label=f"{name} predator");axes[1].plot(data["prey"],data["predator"],label=name)
 axes[0].set(xlabel="time",ylabel="population",title="Periodic populations and phase offset");axes[1].plot(*EQUILIBRIUM,"ko",label="equilibrium");axes[1].set(xlabel="prey",ylabel="predator",title="Closed invariant level sets");axes[0].legend(fontsize=7,ncol=2);axes[1].legend();fig.tight_layout();fig.savefig(output/"population-cycles.png",dpi=180);fig.savefig(output/"phase-portrait.svg");plt.close(fig)
 fig,axis=plt.subplots(figsize=(6,5));stride=200
 def update(frame):
  axis.clear()
  for name,data in trajectories.items():axis.plot(data["prey"][:frame*stride+1],data["predator"][:frame*stride+1],label=name)
  axis.plot(*EQUILIBRIUM,"ko");axis.set(xlabel="prey",ylabel="predator",title="Volterra predator–prey cycles (model time)");axis.legend()
 FuncAnimation(fig,update,frames=101,interval=80).save(output/"predator-prey-cycles.gif",writer=PillowWriter(fps=12));plt.close(fig)
def validate(output,reference=None):
 output=Path(output);required=("scenario-manifest.json","ensemble-metrics.json","ensemble-metrics.csv","population-cycles.png","phase-portrait.svg","predator-prey-cycles.gif");aggregate_result=load(output/"ensemble-metrics.json")
 checks={"three_scenarios":len(aggregate_result["scenarios"])==3,"aggregate_passed":aggregate_result["passed"],"required_files":all((output/x).is_file() and (output/x).stat().st_size for x in required)}
 if reference:
  reference=Path(reference);checks["canonical_metrics_match_reference"]=(output/"ensemble-metrics.csv").read_bytes()==(reference/"ensemble-metrics.csv").read_bytes()
 report={"passed":all(checks.values()),"checks":checks,"sha256":{x:sha256(output/x) for x in required}};dump(output/"validation.json",report)
 if not report["passed"]:raise SystemExit(json.dumps(report,indent=2))
if __name__=="__main__":
 parser=argparse.ArgumentParser();parser.add_argument("stage",choices=("prepare","solve","aggregate","render","validate"));parser.add_argument("--output",required=True);parser.add_argument("--scenario",choices=tuple(SCENARIOS));parser.add_argument("--reference");args=parser.parse_args()
 {"prepare":lambda:prepare(args.output),"solve":lambda:solve(args.scenario,args.output),"aggregate":lambda:aggregate(args.output),"render":lambda:render(args.output),"validate":lambda:validate(args.output,args.reference)}[args.stage]()
