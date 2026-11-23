#!/usr/bin/env python3
import argparse, json, shutil, urllib.request
from pathlib import Path
import matplotlib.pyplot as plt

def fetch(api,token,run):
    req=urllib.request.Request(f"{api}/execution-runs/{run}/",headers={"Authorization":f"Bearer {token}"})
    with urllib.request.urlopen(req) as response: return json.load(response)
def main():
    p=argparse.ArgumentParser(); p.add_argument("--source",required=True); p.add_argument("--output",required=True); p.add_argument("--api",default="http://127.0.0.1:8080/akoflow-api"); p.add_argument("--token",default="akoflow-development-token"); a=p.parse_args(); src=Path(a.source); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    parallel=fetch(a.api,a.token,"community-foucault-run-v1"); serial=fetch(a.api,a.token,"community-foucault-one-slot-run-v1")
    (out/"daemon-run.json").write_text(json.dumps(parallel,indent=2,sort_keys=True)+"\n"); (out/"one-slot-run.json").write_text(json.dumps(serial,indent=2,sort_keys=True)+"\n")
    for name in ("foucault-trajectories.png","precession-vs-latitude.png","foucault-precession.gif","metrics.json","validation.json","manifest.json","inputs.json"):
        shutil.copy2(src/name,out/name)
    branches=[x for x in parallel["activities"] if "latitude-" in x["activityId"]]; base=min(x["startedAt"] for x in parallel["activities"]); fig,ax=plt.subplots(figsize=(10,5))
    for i,x in enumerate(parallel["activities"]):
        label=x["activityId"].split("-v1-")[-1]; ax.barh(i,x["finishedAt"]-x["startedAt"],left=x["startedAt"]-base,color="#222" if x in branches else "#999"); ax.text(x["startedAt"]-base+.2,i,label,va="center",ha="left",color="white",fontsize=8)
    ax.set(xlabel="seconds after first activity start",ylabel="daemon activity",title="Measured five-slot AkôFlow execution timeline"); ax.set_yticks([]); fig.tight_layout(); fig.savefig(out/"measured-timeline.png",dpi=160); plt.close(fig)
    starts=max(x["startedAt"] for x in branches); finishes=min(x["finishedAt"] for x in branches); summary={"parallel_run_id":parallel["run"]["id"],"one_slot_run_id":serial["run"]["id"],"parallel_makespan_seconds":parallel["run"]["makespanSeconds"],"one_slot_makespan_seconds":serial["run"]["makespanSeconds"],"makespan_ratio":serial["run"]["makespanSeconds"]/parallel["run"]["makespanSeconds"],"all_five_branch_overlap_seconds":finishes-starts,"image":"sha256:8386ab8b1681b533f280433bfe583a308d3797e92c17f5fe0c8389876063d0ea"}
    (out/"comparison.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
