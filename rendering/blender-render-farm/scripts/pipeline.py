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
 ext='png' if next((o/'frames').glob('*.png'),None) else 'ppm'
 if shutil.which('ffmpeg'):
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','8','-i',str(o/f'frames/frame-%04d.{ext}'),'-c:v','libx264','-pix_fmt','yuv420p',str(o/'animation.mp4')],check=True);return
 if ext!='ppm':raise SystemExit('ffmpeg is required to compose Blender PNG frames')
 with (o/'animation.y4m').open('wb') as video:
  video.write(b'YUV4MPEG2 W640 H360 F8:1 Ip A1:1 C444\n')
  for frame in sorted((o/'frames').glob('*.ppm')):
   payload=frame.read_bytes().split(b'\n',3)[3];yuv=[bytearray(),bytearray(),bytearray()]
   for i in range(0,len(payload),3):
    r,g,b=payload[i:i+3];yuv[0].append(max(0,min(255,int(.299*r+.587*g+.114*b))));yuv[1].append(max(0,min(255,int(-.169*r-.331*g+.5*b+128))));yuv[2].append(max(0,min(255,int(.5*r-.419*g-.081*b+128))))
   video.write(b'FRAME\n'+yuv[0]+yuv[1]+yuv[2])
def verify(o):
 frames=sorted((o/'frames').glob('frame-*'));video=o/('animation.mp4' if (o/'animation.mp4').exists() else 'animation.y4m');ok=len(frames)==COUNT and video.stat().st_size>1000
 dump(o/'render-report.json',{'status':'passed' if ok else 'failed','expected_frames':COUNT,'rendered_frames':len(frames),'workers':2})
 arts=['render-plan.json','scene.blend',video.name,'render-report.json'];dump(o/'manifest.json',{'showcase':'blender-render-farm','status':'success' if ok else 'failed','artifacts':arts})
S={'setup':setup,'render-even':lambda o:render(o,0),'render-odd':lambda o:render(o,1),'compose':compose,'verify':verify}
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=[*S,'all'],default='all');p.add_argument('--output',required=True);a=p.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=True)
 for s in list(S) if a.stage=='all' else [a.stage]:S[s](o)
if __name__=='__main__':main()
