import json,sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
items=json.loads(Path(sys.argv[1]).read_text()); origin=min(x["startedAt"] for x in items)
fig,axis=plt.subplots(figsize=(11,4.8)); colors={"slot-0":"#111111","slot-1":"#666666","slot-2":"#aaaaaa"}
for row,item in enumerate(items):
 start=item["startedAt"]-origin; duration=item["finishedAt"]-item["startedAt"]
 axis.barh(row,duration,left=start,color=colors[item["resource"]],height=.65);axis.text(start+.05,row,item["activity"],va="center",ha="left",color="white" if item["resource"]!="slot-2" else "black",fontsize=8)
axis.axvspan(1795370418.1838381-origin,1795370419.631669-origin,color="#e63946",alpha=.18,label="measured three-way scientific overlap: 1.448 s")
axis.set(yticks=range(len(items)),yticklabels=[x["resource"] for x in items],xlabel="seconds from first activity start",title="AkôFlow measured activity timeline — run community-volterra-predator-prey-run-v1");axis.invert_yaxis();axis.legend(loc="lower right",frameon=False);fig.tight_layout();fig.savefig(sys.argv[2],dpi=180);plt.close(fig)
