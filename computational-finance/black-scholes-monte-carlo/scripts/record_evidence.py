#!/usr/bin/env python3
import hashlib, json, shutil, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
API="http://127.0.0.1:8080/akoflow-api/execution-runs/"
def get(run):
    request=urllib.request.Request(API+run+"/",headers={"Authorization":"Bearer akoflow-development-token"})
    with urllib.request.urlopen(request) as response:return json.load(response)
def dump(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

parallel=get("community-black-scholes-run-v1")
serial=get("community-black-scholes-one-slot-run-v1")
evidence=ROOT/"evidence"; reference=ROOT/"outputs"/"reference"
shutil.copytree(ROOT/"outputs"/"preflight"/"a",reference,dirs_exist_ok=True)
dump(evidence/"daemon-run.json",parallel);dump(evidence/"daemon-run-one-slot.json",serial)
attempts=parallel["activityAttempts"]
branches=[a for a in attempts if "estimate-seed" in a["activityId"]]
pair_overlaps=[]
for i,a in enumerate(branches):
    for b in branches[i+1:]:
        overlap=max(0.0,min(a["finishedAt"],b["finishedAt"])-max(a["startedAt"],b["startedAt"]))
        if overlap:pair_overlaps.append({"a":a["activityId"],"b":b["activityId"],"seconds":overlap})
comparison={"parallel_run_id":parallel["run"]["id"],"parallel_makespan_seconds":parallel["run"]["makespanSeconds"],"one_slot_run_id":serial["run"]["id"],"one_slot_makespan_seconds":serial["run"]["makespanSeconds"],"makespan_ratio_one_slot_over_parallel":serial["run"]["makespanSeconds"]/parallel["run"]["makespanSeconds"],"measured_estimator_pair_overlaps":pair_overlaps,"speedup_claim":False}
dump(evidence/"comparison.json",comparison)
final_ws=next(w for w in parallel["workspaces"] if w["activityId"].endswith("validate"))
excluded={"checksums.json","validation.json"}
daemon_manifest={x["path"]:x["digest"].removeprefix("sha256:") for x in final_ws["manifest"]["final"] if x["path"] not in excluded}
local_manifest={str(p.relative_to(reference)):sha(p) for p in reference.rglob("*") if p.is_file() and str(p.relative_to(reference)) not in excluded}
common=set(daemon_manifest)&set(local_manifest); mismatch={k:{"daemon":daemon_manifest[k],"local":local_manifest[k]} for k in common if daemon_manifest[k]!=local_manifest[k]}
dump(evidence/"daemon-result-agreement.json",{"checked_common_files":len(common),"mismatches":mismatch,"passed":bool(common) and not mismatch})
base=min(a["startedAt"] for a in attempts);end=max(a["finishedAt"] for a in attempts);scale=900/(end-base); rows=[]
for i,a in enumerate(attempts):
    start=100+(a["startedAt"]-base)*scale; width=max(2,(a["finishedAt"]-a["startedAt"])*scale); label=a["activityId"].replace("community-black-scholes-monte-carlo-v1-",""); color="#111111" if "estimate-seed" in label else "#777777"; y=55+i*42; rows.append(f'<rect x="{start:.2f}" y="{y}" width="{width:.2f}" height="24" fill="{color}"/><text x="{start+4:.2f}" y="{y+17}" font-size="12" fill="black">{label}</text>')
svg='\n'.join(['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="430" viewBox="0 0 1100 430">','<rect width="1100" height="430" fill="white"/>','<text x="550" y="28" text-anchor="middle" font-size="18">Measured AkôFlow daemon timeline — community-black-scholes-run-v1</text>',*rows,'<line x1="100" y1="400" x2="1000" y2="400" stroke="black"/>','<text x="550" y="422" text-anchor="middle" font-size="13">seconds from first activity start</text>','</svg>\n'])
(evidence/"measured-timeline.svg").write_text(svg)
dump(evidence/"image.json",{"id":"sha256:2cd38df1cf969ada9c10c0296cce29f445935f71e41f09518efd01c8810c45f1","reference":"akoflow/community-black-scholes:v1","portable_build_ref":"recipe-build-3813bf5e8fd053915fcd685ce4948e67662a022484d30fd0ceb6b244a5879302","context_digest":"sha256:b78ece52089c87d6027d8b11222438b5e78ef80f8a054e539e84eae4e2a0bdb8","recipe_digest":"sha256:3b7670abfba77615adecada50b936ec53be36988ba48dcde7c52acd438b88dbb"})
if mismatch or not common or parallel["run"]["status"]!="completed" or serial["run"]["status"]!="completed" or not pair_overlaps:raise SystemExit("evidence validation failed")
print(json.dumps(comparison,sort_keys=True))
