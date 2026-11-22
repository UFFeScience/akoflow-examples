#!/usr/bin/env python3
import argparse,csv,hashlib,json,math,struct,zlib
from pathlib import Path
V='community-debye-heat-v1'; N=321; C=12*math.pi**4/5
def js(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
def q(f,a,b,t=1e-13):
 def s(a,b,x,y,z):return (b-a)*(x+4*z+y)/6
 x,y=f(a),f(b);m=(a+b)/2;z=f(m);w=s(a,b,x,y,z)
 def r(a,b,x,y,z,w,t,d):
  m=(a+b)/2;l=(a+m)/2;u=(m+b)/2;xl,xu=f(l),f(u);p=s(a,m,x,z,xl);v=s(m,b,z,y,xu);e=p+v-w
  return p+v+e/15 if d<1 or abs(e)<=15*t else r(a,m,x,z,xl,p,t/2,d-1)+r(m,b,z,y,xu,v,t/2,d-1)
 return r(a,b,x,y,z,w,t,30)
def cf(x):
 if x==0:return 0.
 if x>350:a=math.exp(-x);return x**4*a/(1-a)**2
 a=math.expm1(x);return x**4*(a+1)/a**2
def uf(x):
 if x==0:return 0.
 if x>350:a=math.exp(-x);return x**3*a/(1-a)
 return x**3/math.expm1(x)
def grid():return [10**(-3+i/80) for i in range(N)]
def wr(p,h,rows):
 with p.open('w',newline='') as f:w=csv.writer(f);w.writerow(h);w.writerows(rows)
def prep(o):
 o.mkdir(parents=True,exist_ok=True);wr(o/'grid.csv',('index','tau'),enumerate(grid()));js(o/'manifest.json',{'workflow_version':V,'issue':42,'source':'Peter Debye (1912), DOI 10.1002/andp.19123441404','input':'generated tau=T/Theta_D','grid':'10^(-3+i/80), i=0..320','runtime':'Python 3.11.14 standard library, binary64, no RNG','license':'MIT'})
def solve(o,b):
 if b=='direct':
  inf=q(cf,0,50);wr(o/'direct.csv',('index','tau','cv_over_r'),((i,t,9*t**3*(inf if 1/t>=50 else q(cf,0,1/t))) for i,t in enumerate(grid())))
 elif b=='energy':
  inf=q(uf,0,50);rows=[]
  for i,t in enumerate(grid()):
   y=1/t;z=inf if y>=50 else q(uf,0,y);bd=0 if y>350 else y**3/math.expm1(y);rows.append((i,t,36*t**3*z-9*t**2*bd))
  wr(o/'energy.csv',('index','tau','cv_over_r'),rows)
 elif b=='asymptotic':
  e=abs(q(cf,0,50)/(4*math.pi**4/15)-1);wr(o/'asymptotic.csv',('index','tau','low','high','identity_error'),((i,t,C*t**3,3,e) for i,t in enumerate(grid())))
def rd(p):
 with p.open() as f:return list(csv.DictReader(f))
def agg(o):
 d,e,a=rd(o/'direct.csv'),rd(o/'energy.csv'),rd(o/'asymptotic.csv');z=[]
 for x,y,k in zip(d,e,a):
  t=float(x['tau']);v=float(x['cv_over_r']);u=float(y['cv_over_r']);lo=float(k['low']);z.append((int(x['index']),t,v,u,lo,3,abs(v-u),abs(v/lo-1),abs(v-3)/3))
 wr(o/'debye-curve.csv',('index','tau','direct','energy','low','high','difference','low_error','high_error'),z);lo=[x for x in z if x[7]<.01];hi=[x for x in z if x[8]<.01]
 js(o/'regime-boundaries.json',{'workflow_version':V,'low_one_percent_last':{'index':lo[-1][0],'tau':lo[-1][1]},'high_one_percent_first':{'index':hi[0][0],'tau':hi[0][1]},'max_formulation_absolute_error':max(x[6] for x in z),'minimum_adjacent_increment':min(z[i+1][2]-z[i][2] for i in range(320)),'low_coefficient_relative_error_at_tau_0_001':abs(z[0][2]/z[0][1]**3/C-1),'high_limit_relative_error_at_tau_10':z[-1][8],'integral_identity_relative_error':float(a[0]['identity_error'])})
def png(p,a):
 h=len(a);w=len(a[0])//3;raw=b''.join(b'\0'+bytes(r) for r in a)
 def c(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 p.write_bytes(b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+c(b'IDAT',zlib.compress(raw,9))+c(b'IEND',b''))
def ln(a,x,y,u,v,c):
 dx=abs(u-x);sx=1 if x<u else -1;dy=-abs(v-y);sy=1 if y<v else -1;e=dx+dy
 while 1:
  if 0<=y<len(a) and 0<=x<len(a[0])//3:a[y][3*x:3*x+3]=c
  if x==u and y==v:return
  z=2*e
  if z>=dy:e+=dy;x+=sx
  if z<=dx:e+=dx;y+=sy
def render(o):
 r=rd(o/'debye-curve.csv');p=[[255]*2700 for _ in range(650)];ln(p,60,580,860,580,(20,20,20));ln(p,60,40,60,580,(20,20,20));ln(p,60,85,860,85,(205,35,45));z=[(60+round((math.log10(float(x['tau']))+3)*200),580-round(float(x['direct'])/3.15*500)) for x in r]
 for x,y in zip(z,z[1:]):ln(p,*x,*y,(35,95,190))
 png(o/'debye-heat-capacity.png',p)
 # Deterministic multi-frame GIF, with a valid minimal plotted raster per frame.
 w,h=320,180;d=bytearray(b'GIF89a'+struct.pack('<HH',w,h)+b'\x81\x00\x00'+bytes((255,255,255,20,20,20,35,95,190,205,35,45))+b'!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00')
 for stop in range(0,321,16):
  pix=[0]*(w*h)
  for x,y in z[:stop+1]:pix[min(h-1,max(0,round(y*180/650)))*w+min(w-1,max(0,round(x*320/900)))]=2
  codes=[]
  for x in pix:codes+=(4,x)
  codes+=[5];pk=bytearray(codes[i]|((codes[i+1] if i+1<len(codes) else 0)<<3) for i in range(0,len(codes),2));d+=b'!\xf9\x04\x00\x08\x00\x00\x00,'+struct.pack('<HHHH',0,0,w,h)+b'\x00\x02'
  for i in range(0,len(pk),255):d+=bytes([len(pk[i:i+255])])+pk[i:i+255]
  d+=b'\0'
 d+=b';';(o/'debye-crossover.gif').write_bytes(d)
def val(o,ref=None):
 b=json.loads((o/'regime-boundaries.json').read_text());r=rd(o/'debye-curve.csv');v=[float(x['direct']) for x in r];ch={'grid':len(r)==321,'finite_positive':all(math.isfinite(x) and x>0 for x in v),'monotonic':all(v[i+1]-v[i]>=-1e-11 for i in range(320)),'agreement':b['max_formulation_absolute_error']<=2e-8,'low':b['low_coefficient_relative_error_at_tau_0_001']<=1e-8,'high':b['high_limit_relative_error_at_tau_10']<=5e-4,'identity':b['integral_identity_relative_error']<=1e-10,'boundaries':abs(b['low_one_percent_last']['tau']-.08659643233600653)<1e-15 and abs(b['high_one_percent_first']['tau']-2.23872113856834)<1e-14}
 files=['grid.csv','manifest.json','direct.csv','energy.csv','asymptotic.csv','debye-curve.csv','regime-boundaries.json','debye-heat-capacity.png','debye-crossover.gif'];ch['media']=(o/files[-2]).read_bytes().startswith(b'\x89PNG') and (o/files[-1]).read_bytes().count(b'!\xf9')>1;ch['byte_identical_reference']=ref is None or all((o/f).read_bytes()==(Path(ref)/f).read_bytes() for f in files);js(o/'validation.json',{'overall_pass':all(ch.values()),'checks':ch,'checksums':{f:hashlib.sha256((o/f).read_bytes()).hexdigest() for f in files},'limitations':['universal acoustic-mode model, no material fit','omits optical phonons, electrons, defects, and anharmonicity']})
 if not all(ch.values()):raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--output',default='.');p.add_argument('--branch');p.add_argument('--reference');a=p.parse_args();o=Path(a.output);{'prepare':lambda:prep(o),'solve':lambda:solve(o,a.branch),'aggregate':lambda:agg(o),'render':lambda:render(o),'validate':lambda:val(o,a.reference)}[a.mode]()
if __name__=='__main__':main()
