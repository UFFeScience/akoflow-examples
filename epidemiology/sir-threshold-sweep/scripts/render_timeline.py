import json
from pathlib import Path
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parents[1]
items=json.loads((root/"evidence/measured-activities.json").read_text())
origin=min(item["startedAt"] for item in items)
slots=["slot-0","slot-1","slot-2","slot-3"]
figure,axis=plt.subplots(figsize=(9,3.5))
for item in items:
 y=slots.index(item["resource"]); start=item["startedAt"]-origin; duration=item["finishedAt"]-item["startedAt"]
 axis.barh(y,duration,left=start,height=.55,color=str(.15+.18*y),edgecolor="black")
 axis.text(start+duration/2,y,item["activity"],ha="center",va="center",color="white" if y<2 else "black",fontsize=8)
axis.set_yticks(range(4),slots); axis.set_xlabel("seconds since first scenario start"); axis.set_title("Measured AkôFlow scientific activity timeline")
axis.grid(axis="x",color="0.85"); figure.tight_layout(); figure.savefig(root/"evidence/measured-timeline.png",dpi=180)
