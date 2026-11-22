import json
from pathlib import Path
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parents[1]
items=json.loads((root/"evidence/measured-activities.json").read_text())
origin=min(x["startedAt"] for x in items)
colors=("#2563eb","#16a34a","#dc2626","#9333ea")
fig,axis=plt.subplots(figsize=(11,6.5))
for row,item in enumerate(items):
 name=item["id"].split(":",1)[1].replace("community-ising-yang-v1-","")
 slot=int(name.rsplit("-",1)[1])%4 if name.startswith("sample-shard-") else 0
 start=item["startedAt"]-origin;duration=item["finishedAt"]-item["startedAt"]
 axis.barh(row,duration,left=start,height=.62,color=colors[slot],edgecolor="black")
 axis.text(start+duration/2,row,f"{duration:.2f}s",ha="center",va="center",fontsize=7,color="white",weight="bold")
axis.set_yticks(range(len(items)),[x["id"].split(":",1)[1].replace("community-ising-yang-v1-","") for x in items]);axis.invert_yaxis();axis.set_xlabel("seconds since first activity start");axis.set_title("AkôFlow measured timeline — Yang 2D Ising run v1")
axis.legend(handles=[plt.Rectangle((0,0),1,1,color=color,label=f"slot {i}") for i,color in enumerate(colors)],loc="lower right");axis.grid(axis="x",alpha=.25);fig.tight_layout();fig.savefig(root/"evidence/measured-timeline.png",dpi=180);plt.close(fig)
