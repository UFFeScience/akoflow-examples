#!/usr/bin/env python3
import argparse,json,math,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];COUNT=6 if os.getenv('AKOFLOW_PROFILE','smoke')=='smoke' else 24
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+"\n")
def software(path,frame):
 w,h=640,360;buf=bytearray()
 centers=[(int(w*.25+40*math.sin(frame*.3)),180,(38,115,242)),(int(w*.5+50*math.cos(frame*.25)),160,(242,89,38)),(int(w*.75+35*math.sin(frame*.2)),190,(64,217,115))]
 for y in range(h):
  for x in range(w):
   c=(10+int(20*y/h),13+int(20*y/h),22+int(30*y/h))
   for cx,cy,col in centers:
    if (x-cx)**2+(y-cy)**2<52**2:c=col
   buf.extend(c)
 path.write_bytes(f'P6\n{w} {h}\n255\n'.encode()+buf)
def invoke(o,*args,blend=False):
 cmd=['blender','--background'];
 if blend:cmd.append(str(o/'scene.blend'))
 cmd += ['--python',str(ROOT/'scripts/blender_job.py'),'--',*map(str,args)];subprocess.run(cmd,check=True)
def setup(o):
 (o/'frames').mkdir(parents=True,exist_ok=True)
 if shutil.which('blender'):invoke(o,'setup',o,COUNT)
 elif os.getenv('AKOFLOW_REQUIRE_BLENDER')=='1':raise SystemExit('Blender is required')
 else:dump(o/'scene.blend',{'fixture':'software-render','frames':COUNT})
 dump(o/'render-plan.json',{'frames':COUNT,'shards':{'render-even':'even frames','render-odd':'odd frames'},'engine':'blender' if shutil.which('blender') else 'software-fixture'})
def render(o,parity):
 if shutil.which('blender'):invoke(o,'render',o,parity,COUNT,blend=True)
 else:
  for n in range(1,COUNT+1):
   if n%2==parity:software(o/'frames'/f'frame-{n:04d}.ppm',n)
def compose(o):
 if not shutil.which('ffmpeg'):raise SystemExit('ffmpeg is required')
 ext='png' if next((o/'frames').glob('*.png'),None) else 'ppm'
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','8','-i',str(o/f'frames/frame-%04d.{ext}'),'-c:v','libx264','-pix_fmt','yuv420p',str(o/'animation.mp4')],check=True)
def verify(o):
 frames=sorted((o/'frames').glob('frame-*'));ok=len(frames)==COUNT and (o/'animation.mp4').stat().st_size>1000
 dump(o/'render-report.json',{'status':'passed' if ok else 'failed','expected_frames':COUNT,'rendered_frames':len(frames),'workers':2})
 arts=['render-plan.json','scene.blend','animation.mp4','render-report.json'];dump(o/'manifest.json',{'showcase':'blender-render-farm','status':'success' if ok else 'failed','artifacts':arts})
S={'setup':setup,'render-even':lambda o:render(o,0),'render-odd':lambda o:render(o,1),'compose':compose,'verify':verify}
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=[*S,'all'],default='all');p.add_argument('--output',required=True);a=p.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=True)
 for s in list(S) if a.stage=='all' else [a.stage]:S[s](o)
if __name__=='__main__':main()

