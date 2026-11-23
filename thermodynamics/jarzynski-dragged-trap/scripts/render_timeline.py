#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parents[1]
items=json.loads((root/'evidence/measured-activities.json').read_text())['activities']
parse=lambda x: datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()
lo=min(parse(x['startedAt']) for x in items); hi=max(parse(x['finishedAt']) for x in items)
colors={f'community-jarzynski-slot-{i}':c for i,c in enumerate(['#111111','#2864b7','#d12f3f','#24845c'])}
fig,ax=plt.subplots(figsize=(12,8))
for y,a in enumerate(items):
    start=parse(a['startedAt']); end=parse(a['finishedAt'])
    ax.barh(y,end-start,left=start-lo,color=colors[a['resourceId']])
ax.set_yticks(range(len(items)),[x['activityId'].removeprefix('community-jarzynski-v1-') for x in items],fontsize=7)
ax.invert_yaxis();ax.set_xlabel('seconds after first activity start');ax.set_title('Measured AkôFlow four-slot activity timeline');fig.tight_layout();fig.savefig(root/'evidence/measured-timeline.png',dpi=150);plt.close(fig)

fig,ax=plt.subplots(figsize=(12,7));ax.axis('off')
nodes={'freeze-inputs':(.08,.5),'aggregate':(.68,.5),'render-results':(.82,.5),'validate':(.95,.5),'audit-time-step':(.42,.88),'audit-euler':(.42,.75)}
for i,v in enumerate(('025','050','075','100')):
  for s in range(4):nodes[f'sample-v{v}-s{s}']=(.25+.1*s,.12+.14*i)
for name,(x,y) in nodes.items():
  ax.text(x,y,name,ha='center',va='center',fontsize=7,bbox=dict(boxstyle='round',fc='white',ec='black'))
for name,(x,y) in nodes.items():
  if name!='freeze-inputs':
    target='aggregate' if name.startswith(('sample','audit')) else ('render-results' if name=='aggregate' else ('validate' if name=='render-results' else None))
    if name.startswith(('sample','audit')): ax.annotate('',nodes[name],nodes['freeze-inputs'],arrowprops={'arrowstyle':'->','lw':.5})
    if target: ax.annotate('',nodes[target],nodes[name],arrowprops={'arrowstyle':'->','lw':.5})
ax.set_title('Jarzynski workflow DAG: 16 independent scientific shards and two audits');fig.tight_layout();fig.savefig(root/'evidence/measured-dag.png',dpi=150);plt.close(fig)
