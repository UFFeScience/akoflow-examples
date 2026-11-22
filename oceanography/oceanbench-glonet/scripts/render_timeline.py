import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

data=json.load(open(sys.argv[1],encoding="utf-8")); rows=sorted(data["activities"],key=lambda x:x["startedAt"]); origin=min(x["startedAt"] for x in rows)
colors={f"community-oceanbench-slot-{i}":color for i,color in enumerate(["#111111","#555555","#888888","#BBBBBB"])}
fig,ax=plt.subplots(figsize=(12,7))
for y,item in enumerate(rows):
    start=item["startedAt"]-origin; duration=item["finishedAt"]-item["startedAt"]; resource=item["plannedResourceId"]
    ax.barh(y,duration,left=start,color=colors.get(resource,"#ddd"),edgecolor="black")
    ax.text(start+.1,y,item["activityId"].replace("community-oceanbench-glonet-v1-",""),va="center",fontsize=7,color="white" if resource.endswith(("0","1")) else "black")
ax.set_yticks([]); ax.set_xlabel("Seconds since first activity start"); ax.set_title("Measured AkôFlow timeline — four local CPU slots"); ax.grid(axis="x",alpha=.25)
ax.text(0,-1.2,f"Run {data['run']['id']} · makespan {data['run']['makespanSeconds']:.3f} s",fontsize=8)
fig.tight_layout(); fig.savefig(sys.argv[2],dpi=180)
