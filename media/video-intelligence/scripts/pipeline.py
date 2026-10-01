#!/usr/bin/env python3
import argparse,json,re,shutil,subprocess
from pathlib import Path
def need(x):
 if not shutil.which(x):raise SystemExit(f'{x} is required (or use the provided container)')
def run(args,capture=False):return subprocess.run(args,check=True,text=True,capture_output=capture)
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+"\n")
def ppm(path,color):
 w,h=320,180;path.write_bytes(f'P6\n{w} {h}\n255\n'.encode()+bytes(color)*(w*h))
def prepare(o):
 colors=['0x244b74','0x2f855a','0xb7791f'];freq=[220,330,440]
 if not shutil.which('ffmpeg'):
  dump(o/'source.json',{'format':'offline-video-fixture','duration':6.0,'width':640,'height':360,'fps':12,'colors':colors,'frequencies':freq})
  return
 parts=[]
 for i,(color,hz) in enumerate(zip(colors,freq),1):
  p=o/f'part-{i}.mp4';run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'color=c={color}:s=640x360:d=2:r=12','-f','lavfi','-i',f'sine=frequency={hz}:duration=2','-shortest','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(p)]);parts.append(p)
 listing=o/'concat.txt';listing.write_text(''.join(f"file '{p.name}'\n" for p in parts));run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(o/'source.mp4')])
def probe(o):
 if not shutil.which('ffprobe'):
  source=json.loads((o/'source.json').read_text());dump(o/'probe.json',{'format':{'duration':str(source['duration']),'size':str((o/'source.json').stat().st_size)},'streams':[{'index':0,'codec_type':'video','codec_name':'fixture','width':source['width'],'height':source['height']},{'index':1,'codec_type':'audio','codec_name':'sine'}]});return
 p=run(['ffprobe','-v','error','-show_entries','format=duration,size:stream=index,codec_type,codec_name,width,height','-of','json',str(o/'source.mp4')],True);dump(o/'probe.json',json.loads(p.stdout))
def scenes(o):
 d=o/'thumbnails';d.mkdir(exist_ok=True)
 if shutil.which('ffmpeg'):
  run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(o/'source.mp4'),'-vf','fps=1/2,scale=320:-1',str(d/'scene-%03d.jpg')]);files=sorted(d.glob('*.jpg'))
 else:
  for i,color in enumerate(((36,75,116),(47,133,90),(183,121,31)),1):ppm(d/f'scene-{i:03d}.ppm',color)
  files=sorted(d.glob('*.ppm'))
 dump(o/'scenes.json',[{'scene':i+1,'thumbnail':str(p.relative_to(o))} for i,p in enumerate(files)])
def audio(o):
 if not shutil.which('ffmpeg'):
  dump(o/'audio.json',{'mean_db':-21.1,'peak_db':-18.0,'method':'deterministic-sine-fixture'});return
 p=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(o/'source.mp4'),'-af','volumedetect','-f','null','-'],text=True,capture_output=True)
 mean=re.search(r'mean_volume:\s*([-0-9.]+) dB',p.stderr);peak=re.search(r'max_volume:\s*([-0-9.]+) dB',p.stderr);dump(o/'audio.json',{'mean_db':float(mean.group(1)),'peak_db':float(peak.group(1))})
def timeline(o):
 pr=json.loads((o/'probe.json').read_text());ss=json.loads((o/'scenes.json').read_text());duration=float(pr['format']['duration']);step=duration/max(1,len(ss));items=[{**s,'start_seconds':round(i*step,3),'label':f'Scene {i+1}'} for i,s in enumerate(ss)];dump(o/'timeline.json',{'duration_seconds':duration,'scenes':items})
def report(o):
 source='source.mp4' if (o/'source.mp4').exists() else 'source.json'
 arts=[source,'probe.json','scenes.json','audio.json','timeline.json'];dump(o/'manifest.json',{'showcase':'video-intelligence','status':'success','artifacts':arts})
S={'prepare':prepare,'probe':probe,'scenes':scenes,'audio':audio,'timeline':timeline,'report':report}
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=[*S,'all'],default='all');p.add_argument('--output',required=True);a=p.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=True)
 for s in list(S) if a.stage=='all' else [a.stage]:S[s](o)
if __name__=='__main__':main()
