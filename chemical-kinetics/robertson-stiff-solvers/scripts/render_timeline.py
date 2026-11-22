import json
from datetime import datetime, timezone
from pathlib import Path
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parents[1]
items=json.loads((root/"evidence/measured-activities.json").read_text())
origin=min(x["startedAt"] for x in items)
fig,axis=plt.subplots(figsize=(11,5.5))
colors={"community-robertson-slot-0":"#2563eb","community-robertson-slot-1":"#16a34a","community-robertson-slot-2":"#dc2626"}
for row,item in enumerate(items):
 name=item["activityId"].rsplit("-v1-",1)[-1]
 start=item["startedAt"]-origin;duration=item["finishedAt"]-item["startedAt"]
 axis.barh(row,duration,left=start,height=.62,color=colors[item["resourceId"]],edgecolor="black")
 axis.text(start+duration/2,row,f" {duration:.3f}s",ha="center",va="center",fontsize=8,color="white",weight="bold")
axis.set_yticks(range(len(items)),[x["activityId"].rsplit("-v1-",1)[-1] for x in items]);axis.invert_yaxis();axis.set_xlabel("seconds since first activity start");axis.set_title("AkôFlow measured timeline — Robertson stiff-solvers run v1")
handles=[plt.Rectangle((0,0),1,1,color=color,label=slot.replace("community-robertson-","")) for slot,color in colors.items()];axis.legend(handles=handles,loc="upper right");axis.grid(axis="x",alpha=.25);fig.tight_layout();fig.savefig(root/"evidence/measured-timeline.png",dpi=180);plt.close(fig)
