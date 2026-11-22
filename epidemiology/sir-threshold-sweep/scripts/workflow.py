"""Deterministic Kermack-McKendrick SIR threshold/final-size audit."""
import argparse, csv, hashlib, json, math, platform
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

VALUES=(0.5,0.8,1.0,1.2,1.5,2.0,3.0,5.0)
S0,I0,R_INITIAL,GAMMA=0.999999,0.000001,0.0,1/7
RTOL,ATOL,TERMINAL_I=1e-11,1e-13,5e-13
METHODS=("DOP853","Radau")

def dump(path,value):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def load(path): return json.loads(Path(path).read_text())
def sha256(path):
 digest=hashlib.sha256()
 with Path(path).open("rb") as handle:
  for block in iter(lambda:handle.read(1048576),b""): digest.update(block)
 return digest.hexdigest()
def rhs(q,gamma=GAMMA):
 beta=q*gamma
 return lambda _t,y:(-beta*y[0]*y[1],beta*y[0]*y[1]-gamma*y[1],gamma*y[1])
def analytic_terminal_s(q):
 equation=lambda s:math.log(s/S0)+q*(1-s)
 grid=np.geomspace(1e-15,S0*(1-1e-12),50000); a=grid[0]; fa=equation(a)
 for b in grid[1:]:
  fb=equation(b)
  if fa*fb<0:return float(brentq(equation,a,b,xtol=5e-15,rtol=1e-14))
  a,fa=b,fb
 raise RuntimeError("nontrivial final-size root not bracketed")
def integrate(q,method,gamma=GAMMA,keep_curve=True):
 terminal=lambda _t,y:y[1]-TERMINAL_I
 terminal.terminal,terminal.direction=True,-1
 peak=lambda _t,y:y[0]-1/q
 peak.terminal,peak.direction=False,-1
 solution=solve_ivp(rhs(q,gamma),(0,1e8),(S0,I0,R_INITIAL),method=method,rtol=RTOL,atol=ATOL,events=(terminal,peak),dense_output=True)
 if not solution.success or len(solution.t_events[0])!=1:raise RuntimeError(f"{method} failed terminal event")
 superthreshold=q*S0>1
 if superthreshold and len(solution.y_events[1])==1:peak_time=float(solution.t_events[1][0]); peak_state=solution.y_events[1][0]
 elif superthreshold:raise RuntimeError(f"{method} failed peak event")
 else:peak_time,peak_state=0.0,np.array((S0,I0,R_INITIAL))
 end_time=float(solution.t[-1]); times=np.linspace(0,end_time,241); sample=solution.sol(times)
 result={"method":method,"gamma":gamma,"terminal_time_days":end_time,"terminal":[float(x) for x in solution.y[:,-1]],"peak_time_days":peak_time,"peak":[float(x) for x in peak_state],"mass_error":float(np.max(np.abs(solution.y.sum(0)-1))),"minimum":float(solution.y.min()),"susceptible_increase":float(max(0,np.max(np.diff(solution.y[0])))),"removed_decrease":float(max(0,-np.min(np.diff(solution.y[2]))))}
 if keep_curve:result["curve"]={"time_days":[float(x) for x in times],"susceptible":[float(x) for x in sample[0]],"infected":[float(x) for x in sample[1]],"removed":[float(x) for x in sample[2]]}
 return result
def scenario(output,q):
 runs=[integrate(q,m) for m in METHODS]; analytic=analytic_terminal_s(q); superthreshold=q*S0>1
 derivative=GAMMA*I0*(q*S0-1); residual=abs(math.log(analytic/S0)+q*(1-analytic))
 checks={"finite":all(np.isfinite(r["terminal"]).all() for r in runs),"mass_conserved":max(r["mass_error"] for r in runs)<=1e-10,"nonnegative":min(r["minimum"] for r in runs)>=-1e-12,"susceptible_nonincreasing":max(r["susceptible_increase"] for r in runs)<=1e-12,"removed_nondecreasing":max(r["removed_decrease"] for r in runs)<=1e-12,"threshold_classification":(derivative>0)==superthreshold,"terminal_infected":max(r["terminal"][1] for r in runs)<1e-12,"analytic_residual":residual<=1e-10,"ode_residual":max(abs(math.log(r["terminal"][0]/S0)+q*r["terminal"][2]) for r in runs)<=1e-8,"solver_terminal_agreement":abs(runs[0]["terminal"][0]-runs[1]["terminal"][0])<=1e-8,"analytic_terminal_agreement":max(abs(r["terminal"][0]-analytic) for r in runs)<=1e-8,"solver_peak_agreement":abs(runs[0]["peak"][1]-runs[1]["peak"][1])<=1e-8,"peak_condition":(not superthreshold) or max(abs(r["peak"][0]-1/q) for r in runs)<=1e-7}
 result={"reproduction_number":q,"superthreshold":superthreshold,"initial_infected_derivative":derivative,"analytic_terminal_s":analytic,"analytic_final_size_residual":residual,"runs":runs,"checks":checks,"passed":all(checks.values())}
 dump(Path(output)/"branches"/str(q).replace(".","p")/"result.json",result)
 if not result["passed"]:raise SystemExit(json.dumps(checks,indent=2))
def prepare(output):
 dump(Path(output)/"scenario-manifest.json",{"model":"normalized closed-population deterministic SIR","equations":["dS/dt=-beta*S*I","dI/dt=beta*S*I-gamma*I","dR/dt=gamma*I"],"initial_state":[S0,I0,R_INITIAL],"gamma_per_day":GAMMA,"reproduction_numbers":VALUES,"solvers":METHODS,"rtol":RTOL,"atol":ATOL,"terminal_infected_event":TERMINAL_I,"hard_horizon_days":1e8,"gamma_time_rescaling_tolerance":2e-4,"versions":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,"matplotlib":matplotlib.__version__}})
def fixtures():
 disease_free=solve_ivp(rhs(2.0),(0,28),(1,0,0),rtol=RTOL,atol=ATOL,method="DOP853")
 beta_zero=solve_ivp(rhs(0.0),(0,28),(S0,I0,0),rtol=RTOL,atol=ATOL,method="DOP853")
 derivative=np.array(rhs(2.0)(0,(S0,I0,0)))
 short=solve_ivp(rhs(2.0),(0,1e-5),(S0,I0,0),rtol=1e-13,atol=1e-15,method="DOP853")
 finite_difference=(short.y[:,-1]-np.array((S0,I0,0)))/1e-5
 gamma7=integrate(2.0,"DOP853",GAMMA,False); gamma14=integrate(2.0,"DOP853",1/14,False)
 checks={"disease_free_equilibrium":float(np.max(np.abs(disease_free.y-np.array([[1],[0],[0]]))))<=1e-14,"beta_zero_s_constant":float(np.max(np.abs(beta_zero.y[0]-S0)))<=1e-14,"beta_zero_i_plus_r":float(np.max(np.abs(beta_zero.y[1]+beta_zero.y[2]-I0)))<=1e-12,"short_time_derivative":float(np.max(np.abs(finite_difference-derivative)))<=1e-10,"gamma_final_size_invariant":abs(gamma7["terminal"][0]-gamma14["terminal"][0])<=1e-10,"gamma_time_rescaling":abs(gamma14["terminal_time_days"]/gamma7["terminal_time_days"]-2)<=2e-4}
 return {"checks":checks,"passed":all(checks.values())}
def aggregate(output):
 output=Path(output); scenarios=[load(output/"branches"/str(q).replace(".","p")/"result.json") for q in VALUES]; fixture_results=fixtures()
 result={"passed":all(x["passed"] for x in scenarios) and fixture_results["passed"],"fixtures":fixture_results,"scenarios":scenarios}; dump(output/"aggregate.json",result)
 with (output/"metrics.csv").open("w",newline="") as handle:
  writer=csv.writer(handle,lineterminator="\n"); writer.writerow(["reproduction_number","superthreshold","analytic_terminal_s","dop853_terminal_s","radau_terminal_s","dop853_peak_i","radau_peak_i"])
  for x in scenarios:writer.writerow([format(x["reproduction_number"],".17g"),str(x["superthreshold"]).lower(),format(x["analytic_terminal_s"],".17g"),format(x["runs"][0]["terminal"][0],".17g"),format(x["runs"][1]["terminal"][0],".17g"),format(x["runs"][0]["peak"][1],".17g"),format(x["runs"][1]["peak"][1],".17g")])
def render(output):
 output=Path(output); scenarios=load(output/"aggregate.json")["scenarios"]; figure,axes=plt.subplots(1,3,figsize=(14,4.5))
 for selected,style in ((1.2,"--"),(2.0,"-"),(5.0,":")):
  item=next(x for x in scenarios if x["reproduction_number"]==selected); curve=item["runs"][0]["curve"]; axes[0].plot(curve["time_days"],curve["infected"],style,label=f"R₀={selected:g}")
 axes[0].set(xlabel="time (days)",ylabel="infected fraction",title="Representative epidemics"); axes[0].legend(frameon=False)
 supers=[x for x in scenarios if x["superthreshold"]]; axes[1].semilogy([x["reproduction_number"] for x in supers],[max(abs(r["peak"][0]-1/x["reproduction_number"]) for r in x["runs"]) for x in supers],"ko-"); axes[1].axhline(1e-7,color="0.6",linestyle="--",label="tolerance"); axes[1].set(xlabel="R₀",ylabel="|S at peak − 1/R₀|",title="Peak invariant"); axes[1].legend(frameon=False)
 x=[s["reproduction_number"] for s in scenarios]; axes[2].plot(x,[1-s["analytic_terminal_s"] for s in scenarios],"k-",label="analytic"); axes[2].plot(x,[1-s["runs"][0]["terminal"][0] for s in scenarios],"o",markerfacecolor="white",color="k",label="DOP853"); axes[2].plot(x,[1-s["runs"][1]["terminal"][0] for s in scenarios],"x",color="0.45",label="Radau"); axes[2].set(xlabel="R₀",ylabel="final attack fraction",title="Final-size relation"); axes[2].legend(frameon=False)
 figure.suptitle("Kermack–McKendrick SIR threshold and final-size audit"); figure.tight_layout(); figure.savefig(output/"sir-threshold-final-size.png",dpi=180); figure.savefig(output/"sir-threshold-final-size.svg"); plt.close(figure)
 figure,axis=plt.subplots(figsize=(7,4.5))
 def update(frame):
  axis.clear(); item=scenarios[frame]; curve=item["runs"][0]["curve"]
  for name,label,style in (("susceptible","S","-"),("infected","I","--"),("removed","R",":")):axis.plot(curve["time_days"],curve[name],style,color="k",label=label)
  axis.set(xlabel="time (days)",ylabel="population fraction",ylim=(-.02,1.02),title=f"Parameter sweep (not a forecast): R₀={item['reproduction_number']:g}"); axis.legend(frameon=False,ncol=3)
 animation=FuncAnimation(figure,update,frames=len(scenarios),interval=900); animation.save(output/"sir-parameter-sweep.gif",writer=PillowWriter(fps=1)); plt.close(figure)
def validate(output,reference=None):
 output=Path(output); aggregate_result=load(output/"aggregate.json"); required=("scenario-manifest.json","aggregate.json","metrics.csv","sir-threshold-final-size.png","sir-threshold-final-size.svg","sir-parameter-sweep.gif")
 checks={"eight_scenarios":len(aggregate_result["scenarios"])==8,"aggregate_passed":aggregate_result["passed"],"required_files":all((output/name).is_file() and (output/name).stat().st_size>0 for name in required)}
 if reference:
  reference=Path(reference); checks["canonical_metrics_match_reference"]=(output/"metrics.csv").read_bytes()==(reference/"metrics.csv").read_bytes(); checks["canonical_aggregate_match_reference"]=(output/"aggregate.json").read_bytes()==(reference/"aggregate.json").read_bytes()
 report={"passed":all(checks.values()),"checks":checks,"sha256":{name:sha256(output/name) for name in required}}; dump(output/"validation.json",report)
 if not report["passed"]:raise SystemExit(json.dumps(report,indent=2))
if __name__=="__main__":
 parser=argparse.ArgumentParser(); parser.add_argument("stage",choices=("prepare","scenario","aggregate","render","validate")); parser.add_argument("--output",required=True); parser.add_argument("--r0",type=float); parser.add_argument("--reference"); args=parser.parse_args()
 {"prepare":lambda:prepare(args.output),"scenario":lambda:scenario(args.output,args.r0),"aggregate":lambda:aggregate(args.output),"render":lambda:render(args.output),"validate":lambda:validate(args.output,args.reference)}[args.stage]()
