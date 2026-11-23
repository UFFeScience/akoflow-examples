#!/usr/bin/env python3
import argparse, json, shutil, urllib.request
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

def fetch(api,token,run):
    req=urllib.request.Request(f"{api}/execution-runs/{run}/",headers={"Authorization":f"Bearer {token}"})
    with urllib.request.urlopen(req) as response: return json.load(response)
def main():
    p=argparse.ArgumentParser(); p.add_argument("--source",required=True); p.add_argument("--output",required=True); p.add_argument("--api",default="http://127.0.0.1:8080/akoflow-api"); p.add_argument("--token",default="akoflow-development-token"); a=p.parse_args(); src=Path(a.source); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    parallel=fetch(a.api,a.token,"community-foucault-run-v2"); serial=fetch(a.api,a.token,"community-foucault-one-slot-run-v2")
    (out/"daemon-run.json").write_text(json.dumps(parallel,indent=2,sort_keys=True)+"\n"); (out/"one-slot-run.json").write_text(json.dumps(serial,indent=2,sort_keys=True)+"\n")
    for name in ("foucault-trajectories.png","precession-vs-latitude.png","foucault-precession.gif","metrics.json","validation.json","manifest.json","inputs.json"):
        shutil.copy2(src/name,out/name)
    branches=[x for x in parallel["activities"] if "latitude-" in x["activityId"]]; base=min(x["startedAt"] for x in parallel["activities"]); fig,ax=plt.subplots(figsize=(10,5))
    for i,x in enumerate(parallel["activities"]):
        label=x["activityId"].split("-v2-")[-1]; ax.barh(i,x["finishedAt"]-x["startedAt"],left=x["startedAt"]-base,color="#222" if x in branches else "#999"); ax.text(x["startedAt"]-base+.2,i,label,va="center",ha="left",color="white",fontsize=8)
    ax.set(xlabel="seconds after first activity start",ylabel="daemon activity",title="Measured five-slot AkôFlow execution timeline"); ax.set_yticks([]); fig.tight_layout(); fig.savefig(out/"measured-timeline.png",dpi=160); plt.close(fig)
    durations={x["activityId"].split("-v2-")[-1]:x["finishedAt"]-x["startedAt"] for x in parallel["activities"]}
    nodes=[("freeze-inputs",(0,2)),("latitude-minus-60",(2,4)),("latitude-minus-30",(2,3)),("latitude-zero",(2,2)),("latitude-plus-30",(2,1)),("latitude-plus-60",(2,0)),("aggregate",(4,2)),("render",(6,2)),("validate",(8,2))]
    fig,ax=plt.subplots(figsize=(12,5)); positions=dict(nodes)
    for name,(x,y) in nodes:
        box=FancyBboxPatch((x-.62,y-.28),1.24,.56,boxstyle="round,pad=0.04",facecolor="#222" if "latitude-" in name else "#777",edgecolor="black")
        ax.add_patch(box); ax.text(x,y,f"{name}\n{durations[name]:.2f} s",ha="center",va="center",color="white",fontsize=8)
    edges=[("freeze-inputs",name) for name,_ in nodes if "latitude-" in name]+[(name,"aggregate") for name,_ in nodes if "latitude-" in name]+[("aggregate","render"),("render","validate")]
    for source,target in edges:
        x1,y1=positions[source]; x2,y2=positions[target]; ax.annotate("",xy=(x2-.64,y2),xytext=(x1+.64,y1),arrowprops={"arrowstyle":"->","color":"#555","lw":1.2})
    ax.set(xlim=(-1,9),ylim=(-.7,4.7),title="Measured AkôFlow activity DAG (duration from daemon timestamps)"); ax.axis("off"); fig.tight_layout(); fig.savefig(out/"measured-dag.png",dpi=160); plt.close(fig)
    starts=max(x["startedAt"] for x in branches); finishes=min(x["finishedAt"] for x in branches); summary={"parallel_run_id":parallel["run"]["id"],"one_slot_run_id":serial["run"]["id"],"parallel_makespan_seconds":parallel["run"]["makespanSeconds"],"one_slot_makespan_seconds":serial["run"]["makespanSeconds"],"makespan_ratio":serial["run"]["makespanSeconds"]/parallel["run"]["makespanSeconds"],"all_five_branch_overlap_seconds":finishes-starts,"image":"sha256:73067e54f3391ba33deb7bd2f2b870cf3d5dd89d70cb5510cb005debb254f799"}
    (out/"comparison.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
