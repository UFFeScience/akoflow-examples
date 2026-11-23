#!/usr/bin/env python3
import hashlib,json,os,urllib.request
from pathlib import Path
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parents[1]; evidence=root/"evidence"; evidence.mkdir(exist_ok=True)
api=os.environ.get("AKOFLOW_API_URL","http://127.0.0.1:8080/akoflow-api")
token=os.environ.get("AKOFLOW_API_TOKEN","akoflow-development-token")
ids=("community-henon-map-run-v2","community-henon-map-one-slot-run-v2")
def fetch(run_id):
 req=urllib.request.Request(f"{api}/execution-runs/{run_id}/",headers={"Authorization":f"Bearer {token}"})
 with urllib.request.urlopen(req) as response:return json.load(response)
def compact(payload):
 return {"run":payload["run"],"activities":[{key:item[key] for key in ("activityId","plannedResourceId","status","startedAt","finishedAt","runtimeSeconds","transferSeconds","transferBytes")} for item in payload["activities"]],"events":payload["events"]}
parallel,serial=map(fetch,ids); p=compact(parallel); s=compact(serial)
(evidence/"daemon-run.json").write_text(json.dumps(p,indent=2,sort_keys=True)+"\n")
(evidence/"one-slot-run.json").write_text(json.dumps(s,indent=2,sort_keys=True)+"\n")
branches=[item for item in p["activities"] if "iterate-" in item["activityId"]]
overlap_start=max(x["startedAt"] for x in branches); overlap_end=min(x["finishedAt"] for x in branches)
comparison={"parallel_run_id":ids[0],"one_slot_run_id":ids[1],"parallel_makespan_seconds":p["run"]["makespanSeconds"],"one_slot_makespan_seconds":s["run"]["makespanSeconds"],"measured_speedup":s["run"]["makespanSeconds"]/p["run"]["makespanSeconds"],"four_way_branch_overlap_seconds":overlap_end-overlap_start,"overlap_start":overlap_start,"overlap_end":overlap_end}
(evidence/"comparison.json").write_text(json.dumps(comparison,indent=2,sort_keys=True)+"\n")
items=sorted(p["activities"],key=lambda x:x["startedAt"]); origin=min(x["startedAt"] for x in items); colors={f"community-henon-slot-{i}":c for i,c in enumerate(("#111111","#555555","#888888","#bbbbbb"))}
fig,axis=plt.subplots(figsize=(11,5.8))
for row,item in enumerate(items):
 name=item["activityId"].replace("community-henon-map-v2-",""); start=item["startedAt"]-origin; duration=item["finishedAt"]-item["startedAt"]; color=colors[item["plannedResourceId"]]
 axis.barh(row,duration,left=start,height=.62,color=color,edgecolor="black"); axis.text(start+duration/2,row,f"{duration:.2f}s",ha="center",va="center",fontsize=7,color="white",weight="bold")
axis.set_yticks(range(len(items)),[x["activityId"].replace("community-henon-map-v2-","") for x in items]);axis.invert_yaxis();axis.set_xlabel("seconds since first activity start");axis.set_title("AkôFlow measured timeline — Hénon map audit v2");axis.grid(axis="x",alpha=.25);fig.tight_layout();fig.savefig(evidence/"measured-timeline.png",dpi=180);plt.close(fig)
image=os.environ["AKOFLOW_IMAGE_DIGEST"]
(evidence/"image.json").write_text(json.dumps({"image":"akoflow-reproduced:a94ca2ce90dc9e88343f652b09e879aba74b27a89fb8cc9970fe4fcd1be80d76","digest":image},indent=2,sort_keys=True)+"\n")
checks=[]
for path in sorted((root/"outputs/reference-v1").rglob("*")):
 if path.is_file():checks.append({"path":str(path.relative_to(root)),"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
(evidence/"result-manifest.json").write_text(json.dumps({"files":checks},indent=2,sort_keys=True)+"\n")
