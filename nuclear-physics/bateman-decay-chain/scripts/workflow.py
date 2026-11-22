#!/usr/bin/env python3
import argparse,csv,hashlib,json,math,struct,zlib
from pathlib import Path

VERSION="community-bateman-decay-v1"
REGIMES={"transient":(5.0,2.0,40.0),"secular":(100.0,1.0,30.0),"repeated":(10.0,10.0,80.0)}
def dump(p,o): Path(p).write_text(json.dumps(o,sort_keys=True,separators=(",",":"))+"\n")
def analytic(t,l1,l2):
 n1=math.exp(-l1*t)
 if l1==l2:n2=l1*t*n1
 else:n2=l1*math.exp(-l1*t)*(-math.expm1(-(l2-l1)*t))/(l2-l1)
 return n1,n2,1.0-n1-n2
def deriv(n,l1,l2):return (-l1*n[0],l1*n[0]-l2*n[1],l2*n[1])
def rk4_step(n,h,l1,l2):
 k1=deriv(n,l1,l2);k2=deriv(tuple(n[i]+h*k1[i]/2 for i in range(3)),l1,l2);k3=deriv(tuple(n[i]+h*k2[i]/2 for i in range(3)),l1,l2);k4=deriv(tuple(n[i]+h*k3[i] for i in range(3)),l1,l2)
 return tuple(n[i]+h*(k1[i]+2*k2[i]+2*k3[i]+k4[i])/6 for i in range(3))
def prepare(out):
 out.mkdir(parents=True,exist_ok=True);dump(out/'manifest.json',{"workflow_version":VERSION,"issue":41,"source":"Harry Bateman (1910)","inputs":"synthetic mathematical fractions","units":"days","samples":801,"rk4_substeps_per_interval":100,"regimes":{k:{"parent_half_life":a,"daughter_half_life":b,"end_time":e} for k,(a,b,e) in REGIMES.items()},"runtime":"Python 3.11.14 standard library; binary64; no RNG"})
def solve(out,name):
 h1,h2,end=REGIMES[name];l1=math.log(2)/h1;l2=math.log(2)/h2;dt=end/800;n=(1.0,0.0,0.0);rows=[]
 for i in range(801):
  t=i*dt;a=analytic(t,l1,l2);rows.append((i,t,*a,*n,l1*a[0],l2*a[1]))
  if i<800:
   for _ in range(100):n=rk4_step(n,dt/100,l1,l2)
 fields=('sample','time_days','analytic_n1','analytic_n2','analytic_n3','rk4_n1','rk4_n2','rk4_n3','activity_parent','activity_daughter')
 with (out/f'{name}.csv').open('w',newline='') as f:w=csv.writer(f);w.writerow(fields);w.writerows(rows)
def read(out,name):
 with (out/f'{name}.csv').open() as f:return [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
def aggregate(out):
 result={}
 for name,(h1,h2,end) in REGIMES.items():
  rows=read(out,name);l1=math.log(2)/h1;l2=math.log(2)/h2
  if l1==l2:tp=1/l1;peak=analytic(tp,l1,l2);balance=None
  else:tp=math.log(l2/l1)/(l2-l1);peak=analytic(tp,l1,l2);balance=abs(l1*peak[0]-l2*peak[1])
  result[name]={"samples":len(rows),"max_conservation_error":max(abs(r['analytic_n1']+r['analytic_n2']+r['analytic_n3']-1) for r in rows),"max_rk4_error":max(abs(r[f'analytic_n{i}']-r[f'rk4_n{i}']) for r in rows for i in (1,2,3)),"minimum_population":min(r[f'analytic_n{i}'] for r in rows for i in (1,2,3)),"peak_time_days":tp,"peak_n2":peak[1],"activity_balance_at_peak":balance,"final_activity_ratio":rows[-1]['activity_daughter']/rows[-1]['activity_parent']}
 dump(out/'summary.json',{"workflow_version":VERSION,"regimes":result})
def png(path,p):
 h=len(p);w=len(p[0])//3;raw=b''.join(b'\0'+bytes(r) for r in p)
 def ch(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
def line(p,x0,y0,x1,y1,c,w=1):
 dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
 while True:
  for ox in range(-w,w+1):
   for oy in range(-w,w+1):
    x=x0+ox;y=y0+oy
    if 0<=y<len(p) and 0<=x<len(p[0])//3:p[y][3*x:3*x+3]=c
  if x0==x1 and y0==y1:break
  q=2*e
  if q>=dy:e+=dy;x0+=sx
  if q<=dx:e+=dx;y0+=sy
def gif(path,frames,w,h):
 d=bytearray(b'GIF89a'+struct.pack('<HH',w,h)+b'\x81\x00\x00'+bytes((255,255,255,20,20,20,35,95,190,205,35,45)));d+=b'!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00'
 for fr in frames:
  codes=[]
  for v in fr:codes.extend((4,v))
  codes.append(5);packed=bytearray()
  for i in range(0,len(codes),2):packed.append(codes[i]|((codes[i+1] if i+1<len(codes) else 0)<<3))
  d+=b'!\xf9\x04\x00\x0a\x00\x00\x00,'+struct.pack('<HHHH',0,0,w,h)+b'\x00\x02'
  for i in range(0,len(packed),255):d+=bytes((len(packed[i:i+255]),))+packed[i:i+255]
  d+=b'\x00'
 d+=b';';path.write_bytes(d)
def render(out):
 p=[[255]*2700 for _ in range(650)];cols=((20,20,20),(35,95,190),(205,35,45))
 for panel,(name,(_,_,end)) in enumerate(REGIMES.items()):
  x0=40+panel*300;line(p,x0,580,x0+260,580,cols[0]);line(p,x0,60,x0,580,cols[0]);rows=read(out,name)
  for j,key in enumerate(('analytic_n1','analytic_n2','analytic_n3')):
   pts=[(x0+round(r['time_days']/end*260),580-round(r[key]*500)) for r in rows]
   for a,b in zip(pts,pts[1:]):line(p,*a,*b,cols[j],1)
 png(out/'bateman-regimes.png',p)
 rows=read(out,'transient');frames=[]
 for stop in range(0,801,40):
  fr=[0]*(640*360);linebuf=lambda x0,y0,x1,y1,c:None
  def gl(x0,y0,x1,y1,c):
   dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
   while True:
    if 0<=x0<640 and 0<=y0<360:fr[y0*640+x0]=c
    if x0==x1 and y0==y1:break
    z=2*e
    if z>=dy:e+=dy;x0+=sx
    if z<=dx:e+=dx;y0+=sy
  gl(40,320,610,320,1);gl(40,20,40,320,1)
  for j,key in enumerate(('activity_parent','activity_daughter')):
   pts=[(40+round(r['time_days']/40*570),320-round(r[key]/.35*280)) for r in rows[:stop+1]]
   for a,b in zip(pts,pts[1:]):gl(*a,*b,2+j)
  frames.append(fr)
 gif(out/'activity-equilibrium.gif',frames,640,360)
def validate(out,reference=None):
 summary=json.loads((out/'summary.json').read_text())['regimes'];checks={}
 for name,(h1,h2,end) in REGIMES.items():
  rows=read(out,name);half=analytic(h1,math.log(2)/h1,math.log(2)/h2)[0];s=summary[name]
  checks[name]=len(rows)==801 and all(math.isfinite(v) for r in rows for v in r.values()) and s['minimum_population']>=-5e-14 and s['max_conservation_error']<=5e-13 and s['max_rk4_error']<=2e-9 and abs(half-.5)<=5e-14 and (s['activity_balance_at_peak'] is None or s['activity_balance_at_peak']<=5e-14)
 checks['transient_ratio']=abs(summary['transient']['final_activity_ratio']-5/3)<=5e-4;checks['secular_ratio']=abs(summary['secular']['final_activity_ratio']-100/99)<=2e-9;checks['repeated_peak']=abs(summary['repeated']['peak_time_days']-10/math.log(2))<=5e-13 and abs(summary['repeated']['peak_n2']-math.exp(-1))<=5e-14
 files=['manifest.json','transient.csv','secular.csv','repeated.csv','summary.json','bateman-regimes.png','activity-equilibrium.gif'];det=reference is None or all((out/f).read_bytes()==(Path(reference)/f).read_bytes() for f in files);checks['byte_identical_reference']=det;overall=all(checks.values());dump(out/'validation.json',{"overall_pass":overall,"checks":checks,"checksums":{f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in files},"interpretation":"All populations are mathematical fractions, not real atom counts.","limitations":["synthetic three-member chain, not evaluated nuclear data","no branching, irradiation, uncertainty, emissions, detector response, or dose","repeated-root formula is the continuous limit extension"]})
 if not overall:raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','solve','aggregate','render','validate'));p.add_argument('--output',default='.');p.add_argument('--branch');p.add_argument('--reference');a=p.parse_args();o=Path(a.output);{'prepare':lambda:prepare(o),'solve':lambda:solve(o,a.branch),'aggregate':lambda:aggregate(o),'render':lambda:render(o),'validate':lambda:validate(o,a.reference)}[a.mode]()
if __name__=='__main__':main()
