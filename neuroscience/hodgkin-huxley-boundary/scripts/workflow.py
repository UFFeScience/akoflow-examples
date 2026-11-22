"""Deterministic Hodgkin-Huxley all-or-none excitation audit."""
import argparse, csv, hashlib, json, math, platform, shutil
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np
import scipy
from scipy.integrate import solve_ivp

VALUES=(0.0,2.0,4.0,5.0,6.0,6.25,6.5,6.75,7.0,8.0,10.0)
METHODS=("DOP853","Radau")
RTOL,ATOL,DURATION,STEP=1e-10,1e-12,30.0,0.002
CM,GNA,GK,GL,ENA,EK,EL=1.0,120.0,36.0,0.3,115.0,-12.0,10.613

def dump(path,value):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def load(path): return json.loads(Path(path).read_text())
def sha256(path):
 digest=hashlib.sha256()
 with Path(path).open("rb") as handle:
  for block in iter(lambda:handle.read(1048576),b""): digest.update(block)
 return digest.hexdigest()
def vtrap(x):
 x=float(x)
 return 1-x/2+x*x/12 if abs(x)<1e-7 else x/math.expm1(x)
def rates(v):
 return (0.1*vtrap((10-v)/10),0.125*np.exp(-v/80),vtrap((25-v)/10),4*np.exp(-v/18),0.07*np.exp(-v/20),1/(np.exp((30-v)/10)+1))
def rest_gates():
 an,bn,am,bm,ah,bh=rates(0.0); return (float(am/(am+bm)),float(ah/(ah+bh)),float(an/(an+bn)))
def evaluate(y):
 v,m,h,n=y; an,bn,am,bm,ah,bh=rates(v)
 ina=GNA*m**3*h*(v-ENA); ik=GK*n**4*(v-EK); il=GL*(v-EL)
 return np.asarray((-(ina+ik+il)/CM,am*(1-m)-bm*m,ah*(1-h)-bh*h,an*(1-n)-bn*n)),(ina,ik,il)
def rhs(_t,y): return evaluate(y)[0]
def integrate(v0,method):
 times=np.linspace(0,DURATION,int(DURATION/STEP)+1)
 initial=(v0,*rest_gates())
 solution=solve_ivp(rhs,(0,DURATION),initial,method=method,rtol=RTOL,atol=ATOL,t_eval=times,max_step=0.05)
 if not solution.success or len(solution.t)!=len(times): raise RuntimeError(f"{method} integration failed")
 v,m,h,n=solution.y; currents=np.asarray([evaluate(solution.y[:,i])[1] for i in range(len(times))])
 derivatives=np.asarray([rhs(times[i],solution.y[:,i]) for i in range(len(times))])
 balance=CM*derivatives[:,0]+currents.sum(axis=1)
 indices=np.flatnonzero((v[:-1]<50)&(v[1:]>=50))
 crossing=None
 if len(indices):
  i=int(indices[0]); crossing=float(times[i]+(50-v[i])*(times[i+1]-times[i])/(v[i+1]-v[i]))
 peak=float(np.max(v)); regenerative=crossing is not None and peak>90
 return {"method":method,"successful":True,"peak_voltage_mv":peak,"peak_time_ms":float(times[int(np.argmax(v))]),"crossing_50_mv_ms":crossing,"regenerative":regenerative,"gate_min":float(min(m.min(),h.min(),n.min())),"gate_max":float(max(m.max(),h.max(),n.max())),"current_min_uA_cm2":float(currents.min()),"current_max_uA_cm2":float(currents.max()),"balance_residual_uA_cm2":float(np.max(np.abs(balance))),"curve":{"time_ms":[float(x) for x in times[::50]],"voltage_mv":[float(x) for x in v[::50]],"g_na_ms_cm2":[float(x) for x in (GNA*m**3*h)[::50]],"g_k_ms_cm2":[float(x) for x in (GK*n**4)[::50]]}}
def scenario(output,v0):
 runs=[integrate(v0,m) for m in METHODS]
 peak_delta=abs(runs[0]["peak_voltage_mv"]-runs[1]["peak_voltage_mv"])
 crossing_delta=0.0 if runs[0]["crossing_50_mv_ms"] is None else abs(runs[0]["crossing_50_mv_ms"]-runs[1]["crossing_50_mv_ms"])
 checks={"finite":all(math.isfinite(r["peak_voltage_mv"]) for r in runs),"gates_bounded":min(r["gate_min"] for r in runs)>=-1e-10 and max(r["gate_max"] for r in runs)<=1+1e-10,"balance_residual":max(r["balance_residual_uA_cm2"] for r in runs)<=1e-8,"classification_agreement":runs[0]["regenerative"]==runs[1]["regenerative"],"peak_agreement":peak_delta<=0.05,"crossing_agreement":crossing_delta<=0.01,"zero_control":v0!=0 or max(r["peak_voltage_mv"] for r in runs)<=0.01,"paper_6mv":v0!=6 or (not any(r["regenerative"] for r in runs) and max(r["peak_voltage_mv"] for r in runs)<50),"paper_7mv":v0!=7 or all(r["regenerative"] and r["peak_voltage_mv"]>90 for r in runs)}
 result={"initial_depolarization_mv":v0,"runs":runs,"solver_peak_delta_mv":peak_delta,"solver_crossing_delta_ms":crossing_delta,"checks":checks,"passed":all(checks.values())}
 dump(Path(output)/"branches"/format(v0,"g").replace(".","p")/"result.json",result)
 if not result["passed"]: raise SystemExit(json.dumps(checks,indent=2))
def prepare(output):
 dump(Path(output)/"scenario-manifest.json",{"model":"Hodgkin-Huxley 1952 space-clamped membrane","voltage_convention":"mV relative to rest; positive is depolarization","initial_depolarization_mv":VALUES,"duration_ms":DURATION,"output_interval_ms":STEP,"solvers":METHODS,"rtol":RTOL,"atol":ATOL,"parameters":{"C_m_uF_cm2":CM,"g_Na_mS_cm2":GNA,"g_K_mS_cm2":GK,"g_L_mS_cm2":GL,"E_Na_mv":ENA,"E_K_mv":EK,"E_L_mv":EL,"temperature_c":6.3},"rest_gates":rest_gates(),"versions":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,"matplotlib":matplotlib.__version__}})
def fixtures():
 an10=rates(10)[0]; am25=rates(25)[2]; gates=rest_gates(); derivative=rhs(0,(0,*gates))
 checks={"alpha_n_limit":bool(abs(an10-0.1)<=1e-14),"alpha_m_limit":bool(abs(am25-1.0)<=1e-14),"rest_gates_reference":bool(np.max(np.abs(np.asarray(gates)-np.asarray((0.05293248525724958,0.5961207535084603,0.3176769140606974))))<=1e-14),"rounded_leak_rest_derivative":bool(float(np.max(np.abs(derivative)))<=0.005)}
 return {"checks":checks,"passed":all(checks.values()),"rest_derivative":derivative.tolist()}
def aggregate(output):
 output=Path(output); scenarios=[load(output/"branches"/format(v,"g").replace(".","p")/"result.json") for v in VALUES]; fixture=fixtures()
 regenerative=[x["initial_depolarization_mv"] for x in scenarios if x["runs"][0]["regenerative"]]; subthreshold=[x["initial_depolarization_mv"] for x in scenarios if not x["runs"][0]["regenerative"]]
 bracket=(max(subthreshold),min(regenerative)); bracket_ok=6<=bracket[0]<bracket[1]<=7 and bracket[1]-bracket[0]<=0.25
 result={"passed":all(x["passed"] for x in scenarios) and fixture["passed"] and bracket_ok,"fixtures":fixture,"transition_bracket_mv":bracket,"transition_width_mv":bracket[1]-bracket[0],"scenarios":scenarios}; dump(output/"aggregate.json",result)
 with (output/"metrics.csv").open("w",newline="") as handle:
  writer=csv.writer(handle,lineterminator="\n"); writer.writerow(["initial_depolarization_mv","regenerative","dop853_peak_mv","radau_peak_mv","dop853_crossing_50_ms","radau_crossing_50_ms"])
  for x in scenarios: writer.writerow([format(x["initial_depolarization_mv"],".17g"),str(x["runs"][0]["regenerative"]).lower(),format(x["runs"][0]["peak_voltage_mv"],".17g"),format(x["runs"][1]["peak_voltage_mv"],".17g"),"" if x["runs"][0]["crossing_50_mv_ms"] is None else format(x["runs"][0]["crossing_50_mv_ms"],".17g"),"" if x["runs"][1]["crossing_50_mv_ms"] is None else format(x["runs"][1]["crossing_50_mv_ms"],".17g")])
 if not result["passed"]: raise SystemExit(json.dumps(result,indent=2))
def render(output):
 output=Path(output); scenarios=load(output/"aggregate.json")["scenarios"]; figure,axes=plt.subplots(1,3,figsize=(14,4.5))
 for value,style in ((6.0,"--"),(7.0,"-")):
  curve=next(x for x in scenarios if x["initial_depolarization_mv"]==value)["runs"][0]["curve"]; axes[0].plot(curve["time_ms"],curve["voltage_mv"],style,color="k",label=f"{value:g} mV")
 axes[0].axhline(50,color="0.7",linestyle=":"); axes[0].set(xlabel="time (ms)",ylabel="voltage relative to rest (mV)",title="All-or-none response"); axes[0].legend(frameon=False)
 curve=next(x for x in scenarios if x["initial_depolarization_mv"]==7)["runs"][0]["curve"]; axes[1].plot(curve["time_ms"],curve["g_na_ms_cm2"],"-",color="k",label="Na"); axes[1].plot(curve["time_ms"],curve["g_k_ms_cm2"],"--",color="0.45",label="K"); axes[1].set(xlabel="time (ms)",ylabel="conductance (mS/cm²)",title="7 mV conductances"); axes[1].legend(frameon=False)
 xs=[x["initial_depolarization_mv"] for x in scenarios]; peaks=[x["runs"][0]["peak_voltage_mv"] for x in scenarios]; axes[2].plot(xs,peaks,"ko-"); axes[2].axhline(90,color="0.7",linestyle=":"); axes[2].axvspan(6.75,7,color="0.92"); axes[2].set(xlabel="initial depolarization (mV)",ylabel="peak voltage (mV)",title="Excitation boundary")
 figure.suptitle("Hodgkin–Huxley 1952 excitation audit (6.3 °C)"); figure.tight_layout(); figure.savefig(output/"hh-excitation-boundary.png",dpi=180); figure.savefig(output/"hh-excitation-boundary.svg"); plt.close(figure)
 figure,axis=plt.subplots(figsize=(7,4.5))
 def update(frame):
  axis.clear(); item=scenarios[frame]; curve=item["runs"][0]["curve"]; axis.plot(curve["time_ms"],curve["voltage_mv"],color="k"); axis.axhline(50,color="0.7",linestyle=":"); axis.set(xlabel="time (ms)",ylabel="voltage relative to rest (mV)",ylim=(-15,125),title=f"Initial displacement: {item['initial_depolarization_mv']:g} mV — {'regenerative' if item['runs'][0]['regenerative'] else 'subthreshold'}")
 FuncAnimation(figure,update,frames=len(scenarios),interval=700).save(output/"hh-excitation-sweep.gif",writer=PillowWriter(fps=1.4)); plt.close(figure)
def validate(output,reference=None):
 output=Path(output); aggregate_result=load(output/"aggregate.json"); required=("scenario-manifest.json","aggregate.json","metrics.csv","hh-excitation-boundary.png","hh-excitation-boundary.svg","hh-excitation-sweep.gif")
 checks={"eleven_scenarios":len(aggregate_result["scenarios"])==11,"aggregate_passed":aggregate_result["passed"],"required_files":all((output/n).is_file() and (output/n).stat().st_size>0 for n in required)}
 if reference:
  reference=Path(reference); checks["canonical_metrics_match_reference"]=(output/"metrics.csv").read_bytes()==(reference/"metrics.csv").read_bytes(); checks["canonical_aggregate_match_reference"]=(output/"aggregate.json").read_bytes()==(reference/"aggregate.json").read_bytes()
 report={"passed":all(checks.values()),"checks":checks,"sha256":{n:sha256(output/n) for n in required}}; dump(output/"validation.json",report)
 if not report["passed"]: raise SystemExit(json.dumps(report,indent=2))
 results=output/"results"; results.mkdir(exist_ok=True)
 for name in (*required,"validation.json"): shutil.copy2(output/name,results/name)
 if (results/"branches").exists(): shutil.rmtree(results/"branches")
 shutil.copytree(output/"branches",results/"branches")
if __name__=="__main__":
 parser=argparse.ArgumentParser(); parser.add_argument("stage",choices=("prepare","scenario","aggregate","render","validate")); parser.add_argument("--output",required=True); parser.add_argument("--v0",type=float); parser.add_argument("--reference"); args=parser.parse_args()
 {"prepare":lambda:prepare(args.output),"scenario":lambda:scenario(args.output,args.v0),"aggregate":lambda:aggregate(args.output),"render":lambda:render(args.output),"validate":lambda:validate(args.output,args.reference)}[args.stage]()
