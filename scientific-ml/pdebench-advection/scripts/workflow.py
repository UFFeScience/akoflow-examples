"""Independent, deterministic PDEBench 2022 advection checkpoint audit."""
import argparse, hashlib, json, os, platform, time
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np
import torch
from fno import FNO1d
from unet import UNet1d

N=1000; INITIAL_STEP=10; BATCH=20
INPUT=Path("/inputs")
EXPECTED={"data":"6551dc175b2c345e745a4a0b760025567f9f26e2a0fe3b1eecf068ff0d64afb7","fno":"075b7c247854bdf8113662b951892a0c817de8d37e8ed28ba9359c94f92e9d04","unet":"e09095a9b32e854d21fc7b9fa117ae82e89a12e82aac2f1ae696084d5e7449dd"}
TARGET={"fno":{"nrmse":0.010003877803683281,"predicted_slots_nrmse":0.013230935670435429,"rmse":0.005804695188999176},"unet":{"nrmse":0.029358744621276855,"predicted_slots_nrmse":0.03882930800318718,"rmse":0.016253983601927757}}

def dump(path,obj):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+"\n")
def load(path):return json.loads(Path(path).read_text())
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def truth():
 raw=np.memmap(INPUT/"1D_Advection_Sols_beta4.0.hdf5.head",dtype="<f4",mode="r",offset=2048,shape=(N,201,1024))
 return torch.from_numpy(np.ascontiguousarray(np.transpose(raw[:,::5,::4],(0,2,1))[...,None]))
def prepare(output):
 paths={"data":INPUT/"1D_Advection_Sols_beta4.0.hdf5.head","fno":INPUT/"1D_Advection_Sols_beta4.0_FNO.pt","unet":INPUT/"1D_Advection_Sols_beta4.0_Unet-PF-20.pt"};actual={k:sha(v) for k,v in paths.items()}
 if actual!=EXPECTED:raise SystemExit(f"input checksum mismatch: {actual}")
 dump(Path(output)/"input-provenance.json",{"source":"DaRUS PDEBench releases v1.0/v1.0","licenses":{"data_and_weights":"CC BY 4.0","architectures":"MIT"},"population":{"shape":[1000,256,41,1],"spatial_stride":4,"temporal_stride":5,"initial_step":10},"sha256":actual,"versions":{"python":platform.python_version(),"numpy":np.__version__,"torch":torch.__version__}})
def model(kind):
 if kind=="fno":m=FNO1d(num_channels=1,modes=12,width=20,initial_step=INITIAL_STEP);p=INPUT/"1D_Advection_Sols_beta4.0_FNO.pt"
 else:m=UNet1d(INITIAL_STEP,1);p=INPUT/"1D_Advection_Sols_beta4.0_Unet-PF-20.pt"
 ck=torch.load(p,map_location="cpu");m.load_state_dict(ck["model_state_dict"],strict=True);m.eval();return m,ck
def infer(kind,output):
 torch.set_num_threads(1);y=truth();m,ck=model(kind);grid=(4*torch.arange(256,dtype=torch.float32)/1023).reshape(1,-1,1);parts=[];started=time.perf_counter()
 with torch.inference_mode():
  for begin in range(0,N,BATCH):
   yy=y[begin:begin+BATCH];xx=yy[...,:INITIAL_STEP,:];pred=xx;g=grid.repeat(len(yy),1,1)
   for _ in range(INITIAL_STEP,41):
    flat=xx.reshape(*xx.shape[:-2],-1);im=m(flat,g) if kind=="fno" else m(flat.permute(0,2,1)).permute(0,2,1).unsqueeze(-2);pred=torch.cat((pred,im),-2);xx=torch.cat((xx[...,1:,:],im),-2)
   parts.append(pred.numpy())
 arr=np.concatenate(parts);path=Path(output)/"branches"/kind/"prediction.npy";path.parent.mkdir(parents=True,exist_ok=True);np.save(path,arr,allow_pickle=False)
 dump(path.with_name("inference.json"),{"model":kind,"shape":list(arr.shape),"finite":bool(np.isfinite(arr).all()),"elapsed_seconds":time.perf_counter()-started,"checkpoint_epoch":ck.get("epoch"),"checkpoint_loss":ck.get("loss"),"prediction_sha256":sha(path)})
def metrics(kind,output):
 out=Path(output);y=truth().numpy();p=np.load(out/"branches"/kind/"prediction.npy",mmap_mode="r");error=np.sqrt(np.mean((p-y)**2,axis=1));norm=np.sqrt(np.mean(y**2,axis=1));values={"rmse":float(error.mean()),"nrmse":float((error/norm).mean()),"predicted_slots_nrmse":float((error[:,INITIAL_STEP:]/norm[:,INITIAL_STEP:]).mean()),"max_absolute_error":float(np.max(np.abs(p-y)))}
 checks={k:abs(values[k]-TARGET[kind][k])<=5e-6 for k in TARGET[kind]};dump(out/"branches"/kind/"metrics.json",{"model":kind,**values,"target":TARGET[kind],"checks":checks,"passed":all(checks.values())})
 np.save(out/"branches"/kind/"rmse-by-time.npy",error.mean(axis=(0,2)),allow_pickle=False)
def compare(output):
 out=Path(output);fm=load(out/"branches/fno/metrics.json");um=load(out/"branches/unet/metrics.json");f=np.load(out/"branches/fno/rmse-by-time.npy");u=np.load(out/"branches/unet/rmse-by-time.npy");dump(out/"comparison.json",{"passed":fm["passed"] and um["passed"],"paper_all_slot_nrmse":{"fno":0.01,"unet":0.026},"released_checkpoint_all_slot_nrmse":{"fno":fm["nrmse"],"unet":um["nrmse"]},"documented_discrepancy":"Released U-Net rounds to 2.9e-2, not the printed 2.6e-2."})
 fig,ax=plt.subplots(figsize=(8,5));ax.plot(range(41),f,label="FNO");ax.plot(range(41),u,label="U-Net");ax.axvline(9,color="k",ls="--",label="last copied input");ax.set(xlabel="time slot",ylabel="mean spatial RMSE",title="PDEBench beta=4 advection checkpoint error");ax.legend();fig.tight_layout();fig.savefig(out/"model-error-comparison.png",dpi=180);plt.close(fig)
 y=truth().numpy()[0,:, :,0];fp=np.load(out/"branches/fno/prediction.npy",mmap_mode="r")[0,:,:,0];up=np.load(out/"branches/unet/prediction.npy",mmap_mode="r")[0,:,:,0];fig,axes=plt.subplots(3,1,figsize=(8,7),sharex=True,sharey=True)
 def update(t):
  for ax,label,a in zip(axes,("truth","FNO","U-Net"),(y,fp,up)):ax.clear();ax.plot(a[:,t]);ax.set_ylim(-.15,1.15);ax.set_ylabel(label)
  axes[-1].set_xlabel("space index");fig.suptitle(f"Advection evolution, trajectory 0, slot {t}")
 FuncAnimation(fig,update,frames=range(0,41,2),interval=120).save(out/"advection-evolution.gif",writer=PillowWriter(fps=8));plt.close(fig)
def validate(output,reference=None):
 out=Path(output);required=["input-provenance.json","comparison.json","model-error-comparison.png","advection-evolution.gif","branches/fno/metrics.json","branches/unet/metrics.json"];checks={"required_files":all((out/x).is_file() and (out/x).stat().st_size>0 for x in required),"comparison_passed":load(out/"comparison.json")["passed"],"fno_rounding":round(load(out/"branches/fno/metrics.json")["nrmse"],3)==0.010,"unet_rounding":round(load(out/"branches/unet/metrics.json")["nrmse"],3)==0.029}
 if reference:
  ref=Path(reference);checks["repeat_metrics_within_1e-7"]=all(abs(load(out/f"branches/{k}/metrics.json")[m]-load(ref/f"branches/{k}/metrics.json")[m])<=1e-7 for k in ("fno","unet") for m in TARGET[k])
 dump(out/"validation.json",{"passed":all(checks.values()),"checks":checks,"sha256":{x:sha(out/x) for x in required}})
 if not all(checks.values()):raise SystemExit(json.dumps(checks))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("stage",choices=("prepare","infer","metrics","compare","validate"));p.add_argument("--model",choices=("fno","unet"));p.add_argument("--output",required=True);p.add_argument("--reference");a=p.parse_args();{"prepare":lambda:prepare(a.output),"infer":lambda:infer(a.model,a.output),"metrics":lambda:metrics(a.model,a.output),"compare":lambda:compare(a.output),"validate":lambda:validate(a.output,a.reference)}[a.stage]()
