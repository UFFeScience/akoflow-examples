#!/usr/bin/env python3
import json
from pathlib import Path
from workflow import canvas, line, png, text

root=Path(__file__).resolve().parents[1]
data=json.loads((root/"evidence/measured-activities.json").read_text())
activities=data["activities"]; start=min(a["started_at"] for a in activities); end=max(a["finished_at"] for a in activities)
pix=canvas(1100,580); colors={"community-chsh-slot-0":(0,0,0),"community-chsh-slot-1":(40,100,210),"community-chsh-slot-2":(210,40,40),"community-chsh-slot-3":(40,160,80)}
line(pix,230,520,1050,520,(0,0,0))
for i,a in enumerate(activities):
    y=55+i*50; x0=230+round((a["started_at"]-start)/(end-start)*820); x1=230+round((a["finished_at"]-start)/(end-start)*820)
    line(pix,x0,y,x1,y,colors[a["resource"]],18); text(pix,10,y-8,str(i+1),scale=3)
for i in range(12):
    x=230+round(i/11*820); line(pix,x,515,x,525,(0,0,0)); text(pix,x-10,535,f"{i:02d}",scale=2)
png(root/"evidence/measured-timeline.png",pix)
