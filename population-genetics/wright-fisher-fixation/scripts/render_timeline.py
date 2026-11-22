import json
from pathlib import Path
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1]
items=json.loads((root/'evidence/measured-activities.json').read_text())
origin=min(x['startedAt'] for x in items)
colors={f'community-wf-slot-{i}':c for i,c in enumerate(['#2563eb','#16a34a','#dc2626','#9333ea'])}
fig,ax=plt.subplots(figsize=(12,8))
for row,item in enumerate(items):
 start=item['startedAt']-origin; duration=item['finishedAt']-item['startedAt']
 ax.barh(row,duration,left=start,height=.7,color=colors[item['resourceId']],edgecolor='black')
ax.set_yticks(range(len(items)),[x['activityId'].split('fixation-')[-1] for x in items]);ax.invert_yaxis();ax.set_xlabel('seconds since first shard start');ax.set_title('AkôFlow measured timeline — Wright–Fisher run v1')
ax.grid(axis='x',alpha=.25);fig.tight_layout();fig.savefig(root/'evidence/measured-timeline.png',dpi=180);plt.close(fig)
