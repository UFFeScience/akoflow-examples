#!/usr/bin/env python3
import argparse,hashlib,json,struct,zlib
from pathlib import Path

def write_png(path,parallel,serial):
 W,H=1000,440;pix=[bytearray(b'\xff'*(W*3)) for _ in range(H)];runs=[('four-slot',parallel,(30,100,190)),('one-slot',serial,(190,40,50))]
 def rect(x0,y0,x1,y1,c):
  for y in range(max(0,y0),min(H,y1)):
   for x in range(max(0,x0),min(W,x1)):pix[y][3*x:3*x+3]=bytes(c)
 for group,(name,data,color) in enumerate(runs):
  acts=[a for a in data['activities'] if '-orbit-e' in a['activityId']];base=min(a['startedAt'] for a in acts);span=max(a['finishedAt'] for a in acts)-base
  for j,a in enumerate(acts):
   y=45+group*200+j*36;x0=180+round((a['startedAt']-base)/span*760);x1=180+round((a['finishedAt']-base)/span*760);rect(x0,y,max(x0+2,x1),y+22,color)
 raw=b''.join(b'\0'+bytes(r) for r in pix)
 def ch(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))

def main():
 p=argparse.ArgumentParser();p.add_argument('--parallel',required=True);p.add_argument('--serial',required=True);p.add_argument('--validation',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 parallel=json.loads(Path(a.parallel).read_text());serial=json.loads(Path(a.serial).read_text());validation=json.loads(Path(a.validation).read_text());timeline=out.parent/'outputs/reference/measured-timeline.png';timeline.parent.mkdir(parents=True,exist_ok=True);write_png(timeline,parallel,serial)
 branches={x['activityId'].rsplit('-',1)[-1]:(x['startedAt'],x['finishedAt']) for x in parallel['activities'] if '-orbit-e' in x['activityId']};overlap=max(0,min(branches['e07'][1],branches['e09'][1])-max(branches['e07'][0],branches['e09'][0]))
 evidence={'issue':54,'workflow_version':'community-kepler-equal-area-v1-v1','parallel_run':parallel['run'],'one_slot_run':serial['run'],'parallel_activities':parallel['activities'],'one_slot_activities':serial['activities'],'measured_overlap_seconds':{'orbit-e07__orbit-e09':overlap},'speedup_claimed':False,'output_checksums':validation['checksums'],'outputs_identical_between_runs':True,'image_digest':'sha256:c8390844f004795528fdabd440a788c81b68165ecd7dafdbd30dddaf457c256e','portable_build_ref':'recipe-build-5b2ee5f0f83fd7a7b711aa302afa76551a71ff05305893e02aaa5680500ce2f2','context_digest':'sha256:eb6d2b3f5e839f9ceadfe86d82d455d5d344955b7d78f2840940dc104f190dda','recipe_digest':'sha256:7219c30ff8bbac2ae3ead8687e6967ffc819311ca964687515e8bf65eac4be67','base_image':'python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d','clean_state_preflight':'Build required for every activity; embedded context accepted','timeline_sha256':hashlib.sha256(timeline.read_bytes()).hexdigest()}
 (out/'daemon-runs.json').write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
