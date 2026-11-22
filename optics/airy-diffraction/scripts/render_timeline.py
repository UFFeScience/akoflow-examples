#!/usr/bin/env python3
import json,struct,zlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];aa=json.loads((root/'evidence/measured-activities.json').read_text())['activities'];lo=min(x['started_at'] for x in aa);hi=max(x['finished_at'] for x in aa);w,h=1100,420;pix=[[255]*(w*3) for _ in range(h)];colors={'community-airy-slot-0':(20,20,20),'community-airy-slot-1':(35,95,190),'community-airy-slot-2':(205,35,45)}
def line(x0,y0,x1,y1,c,r=1):
 dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
 while True:
  for xx in range(max(0,x0-r),min(w,x0+r+1)):
   for yy in range(max(0,y0-r),min(h,y0+r+1)):pix[yy][3*xx:3*xx+3]=c
  if x0==x1 and y0==y1:break
  q=2*e
  if q>=dy:e+=dy;x0+=sx
  if q<=dx:e+=dx;y0+=sy
line(160,370,1050,370,(0,0,0))
for i,a in enumerate(aa):
 x0=160+round((a['started_at']-lo)/(hi-lo)*890);x1=160+round((a['finished_at']-lo)/(hi-lo)*890);line(x0,45+i*50,x1,45+i*50,colors[a['resource']],4)
raw=b''.join(b'\0'+bytes(r) for r in pix)
def ch(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
(root/'evidence/measured-timeline.png').write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
# Compact dependency diagram: prepare -> three solver nodes -> aggregate -> render -> validate.
w,h=1100,420;pix=[[255]*(w*3) for _ in range(h)]
nodes=[(70,185),(310,65),(310,185),(310,305),(570,185),(790,185),(990,185)]
for a,b in ((0,1),(0,2),(0,3),(1,4),(2,4),(3,4),(4,5),(5,6)):line(nodes[a][0],nodes[a][1],nodes[b][0],nodes[b][1],(20,20,20),2)
for i,(x,y) in enumerate(nodes):
 c=(35,95,190) if i in (1,2,3) else (20,20,20)
 line(x-28,y-18,x+28,y-18,c,3);line(x+28,y-18,x+28,y+18,c,3);line(x+28,y+18,x-28,y+18,c,3);line(x-28,y+18,x-28,y-18,c,3)
raw=b''.join(b'\0'+bytes(r) for r in pix)
(root/'evidence/measured-dag.png').write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
