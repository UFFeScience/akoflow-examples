"""Deterministic Turing instability test with Schnakenberg kinetics."""
import argparse, csv, hashlib, json, math, platform
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

VERSION="community-turing-schnakenberg-v1"
L=20.0; A=0.1; B=0.9; DU=1.0; SEED=20261122; END=60.0
BRANCHES={
 "primary-128":{"n":128,"dv":10.0,"dt":0.02},
 "primary-64":{"n":64,"dv":10.0,"dt":0.02},
 "control-5":{"n":128,"dv":5.0,"dt":0.02},
 "control-1":{"n":128,"dv":1.0,"dt":0.02},
 "halfstep":{"n":128,"dv":10.0,"dt":0.01},
}

def dump(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def load(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dispersion(dv,n=128):
 modes=[];best=None
 for nx in range(n//2+1):
  for ny in range(n//2+1):
   if nx==ny==0:continue
   shell=nx*nx+ny*ny;q=(2*math.pi/L)**2*shell
   aa=.8-DU*q;dd=-1-dv*q;det=aa*dd+1.8;tr=aa+dd
   growth=(tr+math.sqrt(max(0.0,tr*tr-4*det)))/2
   row={"nx":nx,"ny":ny,"shell":shell,"q":q,"growth":growth};modes.append(row)
   if best is None or growth>best["growth"]:best=row
 return modes,best

def initial(n):
 x=np.arange(n)*L/n;X,Y=np.meshgrid(x,x,indexing="ij");rng=np.random.Generator(np.random.PCG64(SEED));z=[]
 for species in range(2):
  field=np.zeros((n,n))
  rng=np.random.Generator(np.random.PCG64(SEED))
  for nx in range(-8,9):
   for ny in range(-8,9):
    if nx==ny==0:continue
    p1,p2=rng.uniform(0,2*np.pi,2);c1,c2=rng.normal(size=2);phase=2*np.pi*(nx*X+ny*Y)/L
    field+=(c1 if species==0 else c2)*np.cos(phase+(p1 if species==0 else p2))
  field-=field.mean();field*=1e-4/field.std();z.append(field)
 return 1.0+z[0],0.9+z[1]

def prepare(output):
 output=Path(output);modes,best=dispersion(10.0);controls={str(dv):dispersion(dv)[1] for dv in (5.0,1.0)}
 manifest={"version":VERSION,"model":"Schnakenberg reaction-diffusion","domain":{"boundary":"periodic","L":L},"kinetics":{"a":A,"b":B,"Du":DU,"equilibrium":[1.0,0.9],"jacobian":[[.8,1.0],[-1.8,-1.0]],"trace":-.2,"determinant":1.0},"seed":SEED,"rng":"NumPy PCG64","perturbationStd":1e-4,"modeLimit":8,"solver":"Fourier pseudospectral CNAB2","endTime":END,"fitWindow":[20.0,60.0],"sampleInterval":0.5,"analysisFloor":1e-12,"branches":BRANCHES,"analytic":{"unstableQ":[.2,.5],"fastestDiscrete":best,"controls":controls},"versions":{"python":platform.python_version(),"numpy":np.__version__,"matplotlib":matplotlib.__version__}}
 dump(output/"scenario-manifest.json",manifest)
 with (output/"dispersion.csv").open("w",newline="") as handle:
  writer=csv.DictWriter(handle,fieldnames=("nx","ny","shell","q","growth"),lineterminator="\n");writer.writeheader();writer.writerows(modes)
 for n in (64,128):
  u,v=initial(n);np.savez(output/f"initial-{n}.npz",u=u,v=v)

def simulate(output,branch):
 output=Path(output);spec=BRANCHES[branch];n=spec["n"];dv=spec["dv"];dt=spec["dt"]
 data=np.load(output/f"initial-{n}.npz",allow_pickle=False);u=data["u"].copy();v=data["v"].copy()
 freq=2*np.pi*np.fft.fftfreq(n,d=L/n);kx,ky=np.meshgrid(freq,freq,indexing="ij");k2=kx*kx+ky*ky;shell=np.rint((L/(2*np.pi))**2*k2).astype(int)
 times=[];amplitudes=[];frames=[];prev_ru=prev_rv=None;stride=round(.5/dt);steps=round(END/dt)
 for step in range(steps+1):
  if step%stride==0:
   uh=np.fft.fft2(u-u.mean());vh=np.fft.fft2(v-v.mean());times.append(step*dt)
   amplitudes.append([math.sqrt(float(np.sum(np.abs(uh[shell==s])**2+np.abs(vh[shell==s])**2)))/n**2 for s in range(65)])
   if branch=="primary-128" and step%(stride*10)==0:frames.append((u-1.0).copy())
  if step==steps:break
  uv2=u*u*v;ru=A-u+uv2;rv=B-uv2
  nru=ru if prev_ru is None else 1.5*ru-.5*prev_ru;nrv=rv if prev_rv is None else 1.5*rv-.5*prev_rv
  uh=((1-dt*DU*k2/2)*np.fft.fft2(u)+dt*np.fft.fft2(nru))/(1+dt*DU*k2/2)
  vh=((1-dt*dv*k2/2)*np.fft.fft2(v)+dt*np.fft.fft2(nrv))/(1+dt*dv*k2/2)
  prev_ru,prev_rv=ru,rv;u=np.fft.ifft2(uh).real;v=np.fft.ifft2(vh).real
 target=output/"branches"/branch;target.mkdir(parents=True,exist_ok=True)
 np.savez(target/"result.npz",u=u,v=v,times=np.asarray(times),amplitudes=np.asarray(amplitudes),frames=np.asarray(frames))
 t=np.asarray(times);a4=np.asarray(amplitudes)[:,4];mask=(t>=20)&(t<=60);coef=np.polyfit(t[mask],np.log(a4[mask]),1);fit=np.polyval(coef,t[mask]);y=np.log(a4[mask]);r2=1-float(np.sum((y-fit)**2)/np.sum((y-y.mean())**2))
 final=np.asarray(amplitudes)[-1];dominant=1+int(np.argmax(final[1:]));dump(target/"summary.json",{**spec,"branch":branch,"slopeShell4":float(coef[0]),"r2Shell4":r2,"dominantShell":dominant,"minU":float(u.min()),"minV":float(v.min()),"resultSha256":sha(target/"result.npz")})

def down(a):
 h=np.fft.fftshift(np.fft.fft2(a-a.mean()));return np.fft.ifft2(np.fft.ifftshift(h[32:96,32:96])).real/4
def aggregate(output):
 output=Path(output);summary={name:load(output/"branches"/name/"summary.json") for name in BRANCHES};arrays={name:np.load(output/"branches"/name/"result.npz",allow_pickle=False) for name in BRANCHES}
 p,h=arrays["primary-128"],arrays["halfstep"]
 timestep=float(np.sqrt(np.linalg.norm(p["u"]-h["u"])**2+np.linalg.norm(p["v"]-h["v"])**2)/np.sqrt(np.linalg.norm(h["u"]-h["u"].mean())**2+np.linalg.norm(h["v"]-h["v"].mean())**2))
 c=arrays["primary-64"];du,dv=down(p["u"]),down(p["v"]);resolution=float(np.sqrt(np.linalg.norm(du-(c["u"]-c["u"].mean()))**2+np.linalg.norm(dv-(c["v"]-c["v"].mean()))**2)/np.sqrt(np.linalg.norm(c["u"]-c["u"].mean())**2+np.linalg.norm(c["v"]-c["v"].mean())**2))
 dump(output/"analysis.json",{"summaries":summary,"analyticGrowth":0.044676318319031516,"timestepRelativeL2":timestep,"resolutionRelativeL2":resolution})

def render(output):
 output=Path(output);names=("primary-128","control-5","control-1");fig,axes=plt.subplots(2,3,figsize=(12,7))
 for j,name in enumerate(names):
  d=np.load(output/"branches"/name/"result.npz",allow_pickle=False);axes[0,j].imshow(d["u"]-1,cmap="RdBu_r",origin="lower");axes[0,j].set_title(name);axes[0,j].axis("off")
  for shell in (1,4,5):axes[1,j].plot(d["times"],d["amplitudes"][:,shell],label=f"shell {shell}")
  axes[1,j].set_yscale("log");axes[1,j].set(xlabel="time",ylabel="mode amplitude");axes[1,j].legend()
 fig.tight_layout();fig.savefig(output/"turing-pattern-selection.png",dpi=180);plt.close(fig)
 d=np.load(output/"branches"/"primary-128"/"result.npz",allow_pickle=False);frames=d["frames"]
 fig,ax=plt.subplots(figsize=(5,4));im=ax.imshow(frames[0],cmap="RdBu_r",origin="lower",vmin=frames.min(),vmax=frames.max());ax.axis("off")
 def update(i):im.set_data(frames[i]);ax.set_title(f"Dv=10, t={i*5:g}");return (im,)
 FuncAnimation(fig,update,frames=len(frames),interval=250).save(output/"pattern-emergence.gif",writer=PillowWriter(fps=4));plt.close(fig)

def validate(output,reference=None):
 output=Path(output);analysis=load(output/"analysis.json");s=analysis["summaries"];manifest=load(output/"scenario-manifest.json");checks={
  "equilibrium":manifest["kinetics"]["equilibrium"]==[1.0,.9] and abs(manifest["kinetics"]["trace"]+.2)<1e-12 and abs(manifest["kinetics"]["determinant"]-1)<1e-12,
  "analyticMode":manifest["analytic"]["fastestDiscrete"]["shell"]==4 and abs(manifest["analytic"]["fastestDiscrete"]["q"]-.3947841760435743)<1e-12 and abs(manifest["analytic"]["fastestDiscrete"]["growth"]-.044676318319031516)<1e-12,
  "controlsAnalytic":all(manifest["analytic"]["controls"][str(x)]["growth"]<0 for x in (5.0,1.0)),
  "measuredGrowth":abs(s["primary-128"]["slopeShell4"]-analysis["analyticGrowth"])<=.005 and s["primary-128"]["r2Shell4"]>=.99,
  "dominantMode":s["primary-128"]["dominantShell"]==s["primary-64"]["dominantShell"]==4,
  "controlsDecay":s["control-5"]["slopeShell4"]<0 and s["control-1"]["slopeShell4"]<0,
  "finitePositive":all(x["minU"]>0 and x["minV"]>0 and np.isfinite(x["slopeShell4"]) for x in s.values()),
  "timestepConvergence":analysis["timestepRelativeL2"]<=1e-3,
  "resolutionConvergence":analysis["resolutionRelativeL2"]<=.02,
 }
 required=("scenario-manifest.json","dispersion.csv","analysis.json","turing-pattern-selection.png","pattern-emergence.gif");checks["requiredFiles"]=all((output/x).is_file() and (output/x).stat().st_size for x in required)
 if reference:
  reference=Path(reference);checks["repeatResults"]=all((output/"branches"/x/"result.npz").read_bytes()==(reference/"branches"/x/"result.npz").read_bytes() for x in BRANCHES);checks["repeatAnalysis"]=(output/"analysis.json").read_bytes()==(reference/"analysis.json").read_bytes()
 inventory={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob("*")) if p.is_file() and p.name not in ("validation.json","manifest.json")};report={"passed":all(checks.values()),"checks":checks,"analysis":analysis,"inventory":inventory};dump(output/"validation.json",report);dump(output/"manifest.json",{"files":inventory,"validationPassed":report["passed"]})
 if not report["passed"]:raise SystemExit(json.dumps(report,indent=2))

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("stage",choices=("prepare","simulate","aggregate","render","validate"));p.add_argument("--output",required=True);p.add_argument("--branch",choices=BRANCHES);p.add_argument("--reference");a=p.parse_args();{"prepare":lambda:prepare(a.output),"simulate":lambda:simulate(a.output,a.branch),"aggregate":lambda:aggregate(a.output),"render":lambda:render(a.output),"validate":lambda:validate(a.output,a.reference)}[a.stage]()
