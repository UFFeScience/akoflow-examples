#!/usr/bin/env python3
import hashlib, json, shutil, urllib.request
from pathlib import Path
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]; API="http://127.0.0.1:8080/akoflow-api/execution-runs/"
def get(run):
    req=urllib.request.Request(API+run+"/",headers={"Authorization":"Bearer akoflow-development-token"})
    with urllib.request.urlopen(req) as r:return json.load(r)
def dump(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
parallel=get("community-rabi-run-v1"); serial=get("community-rabi-one-slot-run-v1"); evidence=ROOT/"evidence"; reference=ROOT/"outputs"/"reference"
if reference.exists():shutil.rmtree(reference)
shutil.copytree(ROOT/"outputs"/"preflight"/"a",reference)
dump(evidence/"daemon-run.json",parallel);dump(evidence/"daemon-run-one-slot.json",serial)
attempts=parallel["activityAttempts"]
branches=[a for a in attempts if "solve-" in a["activityId"]]
latest_start=max(a["startedAt"] for a in branches);earliest_finish=min(a["finishedAt"] for a in branches);overlap=max(0.0,earliest_finish-latest_start)
comparison={"parallel_run_id":parallel["run"]["id"],"parallel_makespan_seconds":parallel["run"]["makespanSeconds"],"one_slot_run_id":serial["run"]["id"],"one_slot_makespan_seconds":serial["run"]["makespanSeconds"],"makespan_ratio_one_slot_over_parallel":serial["run"]["makespanSeconds"]/parallel["run"]["makespanSeconds"],"four_branch_common_overlap_seconds":overlap,"speedup_claim":False}
dump(evidence/"comparison.json",comparison)
final_ws=next(w for w in parallel["workspaces"] if w["activityId"].endswith("validate"));daemon_manifest={x["path"]:x["digest"].removeprefix("sha256:") for x in final_ws["manifest"]["initial"]}
local_manifest={str(p.relative_to(reference)):sha(p) for p in reference.rglob("*") if p.is_file() and p.name not in ("manifest.json","validation.json")}
mismatch={k:{"daemon":v,"local":local_manifest.get(k)} for k,v in daemon_manifest.items() if k in local_manifest and local_manifest[k]!=v}
dump(evidence/"daemon-result-agreement.json",{"checked_common_files":len(set(daemon_manifest)&set(local_manifest)),"mismatches":mismatch,"passed":not mismatch})
base=min(a["startedAt"] for a in attempts); fig,ax=plt.subplots(figsize=(11,5),constrained_layout=True)
for i,a in enumerate(attempts):
    start=a["startedAt"]-base; duration=a["finishedAt"]-a["startedAt"]; label=a["activityId"].replace("community-rabi-oscillations-v1-",""); ax.barh(i,duration,left=start,color="#1565c0" if "solve-" in label else "#666666"); ax.text(start+.05,i,label,va="center",fontsize=8,color="white" if duration>1 else "black")
ax.set(yticks=[],xlabel="seconds from first activity start",title="Measured Akoflow daemon timeline — community-rabi-run-v1");ax.grid(axis="x",alpha=.25);fig.savefig(evidence/"measured-timeline.png",dpi=150,metadata={"Software":"Akoflow Community Explorer"});plt.close(fig)
image={"id":"sha256:dc6aa74d7b3ce39bb11f2d94e7717bf3297a3ff7a91a0223e5ea701f1c5c079f","reference":"akoflow/community-rabi:v1"};dump(evidence/"image.json",image)
if mismatch or parallel["run"]["status"]!="completed" or serial["run"]["status"]!="completed" or overlap<=0:raise SystemExit("evidence validation failed")
print(json.dumps(comparison,sort_keys=True))
