#!/usr/bin/env python3
import hashlib,json,shutil,urllib.request
from pathlib import Path
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];API="http://127.0.0.1:8080/akoflow-api/execution-runs/"
def get(run):
 req=urllib.request.Request(API+run+"/",headers={"Authorization":"Bearer akoflow-development-token"})
 with urllib.request.urlopen(req) as r:return json.load(r)
def dump(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
parallel=get("community-percolation-run-v2");serial=get("community-percolation-one-slot-run-v2");evidence=ROOT/"evidence";reference=ROOT/"outputs"/"reference"
if reference.exists():shutil.rmtree(reference)
shutil.copytree(ROOT/"outputs"/"preflight"/"a",reference)
dump(evidence/"daemon-run.json",parallel);dump(evidence/"daemon-run-one-slot.json",serial)
attempts=parallel["activityAttempts"];branches=[a for a in attempts if "sample-l256" in a["activityId"]]
overlap=max(0.0,min(a["finishedAt"] for a in branches)-max(a["startedAt"] for a in branches))
comparison={"parallel_run_id":parallel["run"]["id"],"parallel_makespan_seconds":parallel["run"]["makespanSeconds"],"one_slot_run_id":serial["run"]["id"],"one_slot_makespan_seconds":serial["run"]["makespanSeconds"],"makespan_ratio_one_slot_over_parallel":serial["run"]["makespanSeconds"]/parallel["run"]["makespanSeconds"],"four_l256_branch_common_overlap_seconds":overlap,"speedup_claim":False}
dump(evidence/"comparison.json",comparison)
final_ws=next(w for w in parallel["workspaces"] if w["activityId"].endswith("validate"));daemon_manifest={x["path"]:x["digest"].removeprefix("sha256:") for x in final_ws["manifest"]["initial"]}
local_manifest={str(p.relative_to(reference)):sha(p) for p in reference.rglob("*") if p.is_file() and p.name not in ("checksums.json","validation.json")}
common=set(daemon_manifest)&set(local_manifest);mismatch={k:{"daemon":daemon_manifest[k],"local":local_manifest[k]} for k in common if daemon_manifest[k]!=local_manifest[k]}
dump(evidence/"daemon-result-agreement.json",{"checked_common_files":len(common),"mismatches":mismatch,"passed":bool(common) and not mismatch})
base=min(a["startedAt"] for a in attempts);fig,ax=plt.subplots(figsize=(12,7),constrained_layout=True)
for i,a in enumerate(attempts):
 start=a["startedAt"]-base;duration=a["finishedAt"]-a["startedAt"];label=a["activityId"].replace("community-newman-ziff-percolation-v2-","");ax.barh(i,duration,left=start,color="#222222" if "sample-" in label else "#777777");ax.text(start+.04,i,label,va="center",fontsize=7,color="white" if duration>1 else "black")
ax.set(yticks=[],xlabel="seconds from first activity start",title="Measured Akoflow daemon timeline — community-percolation-run-v2");ax.grid(axis="x",alpha=.25);fig.savefig(evidence/"measured-timeline.png",dpi=150,metadata={"Software":"Akoflow Community Explorer"});plt.close(fig)
dump(evidence/"image.json",{"id":"sha256:c9d1717d594b991cc6d04ea04abacef3cf502f0d65333888dc59275fb1c5ceb8","reference":"akoflow/community-percolation:v1"})
if mismatch or not common or parallel["run"]["status"]!="completed" or serial["run"]["status"]!="completed" or overlap<=0:raise SystemExit("evidence validation failed")
print(json.dumps(comparison,sort_keys=True))
