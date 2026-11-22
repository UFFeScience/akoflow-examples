import json
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parents[1]
events=json.loads((root/"evidence/activity-events.json").read_text())
def stamp(value):return datetime.fromisoformat(value.replace("Z","+00:00")).timestamp()
starts={x["activityId"]:stamp(x["occurredAt"]) for x in events if x["eventType"]=="activity.started"}
ends={x["activityId"]:stamp(x["occurredAt"]) for x in events if x["eventType"]=="activity.completed"}
items=[{"id":key,"startedAt":starts[key],"finishedAt":ends[key]} for key in starts if key in ends]
items.sort(key=lambda x:x["startedAt"])
(root/"evidence/measured-activities.json").write_text(json.dumps(items,indent=2)+"\n")
origin=min(x["startedAt"] for x in items);colors=("#2563eb","#16a34a","#dc2626","#9333ea")
slots={"prepare-scenario":0,"integrate-reference":0,"integrate-perturb-x":1,"integrate-perturb-y":2,"integrate-perturb-z":3,"aggregate-analysis":0,"render-results":0,"validate":0}
fig,axis=plt.subplots(figsize=(11,5.8))
for row,item in enumerate(items):
 name=item["id"].replace("community-lorenz-sensitivity-v1-","");slot=slots[name];start=item["startedAt"]-origin;duration=item["finishedAt"]-item["startedAt"]
 axis.barh(row,duration,left=start,height=.62,color=colors[slot],edgecolor="black");axis.text(start+duration/2,row,f"{duration:.2f}s",ha="center",va="center",fontsize=7,color="white",weight="bold")
axis.set_yticks(range(len(items)),[x["id"].replace("community-lorenz-sensitivity-v1-","") for x in items]);axis.invert_yaxis();axis.set_xlabel("seconds since first activity start");axis.set_title("AkôFlow measured timeline — Lorenz sensitivity run v1");axis.legend(handles=[plt.Rectangle((0,0),1,1,color=c,label=f"slot {i}") for i,c in enumerate(colors)],loc="lower right");axis.grid(axis="x",alpha=.25);fig.tight_layout();fig.savefig(root/"evidence/measured-timeline.png",dpi=180);plt.close(fig)
