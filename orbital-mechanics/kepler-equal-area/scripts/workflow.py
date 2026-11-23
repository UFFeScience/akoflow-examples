#!/usr/bin/env python3
import argparse,csv,hashlib,json,math,struct,zlib
from pathlib import Path
V='community-kepler-equal-area-v1'; ES=(0.0,0.3,0.7,0.9); N=4096
REF={0.0:(1.5707963267948966,3.1415926535897931,4.7123889803846897),0.3:(1.8584684120533297,3.1415926535897931,4.4247168951262568),0.7:(2.1547852931018419,3.1415926535897931,4.1284000140777444),0.9:(2.2634151063569425,3.1415926535897931,4.0197702008226432)}
def js(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
def tag(e):return f'{int(round(e*10)):02d}'
def solve_e(m,e):
 if e==0:return m
 lo,hi=m-e,m+e;x=m
 for _ in range(80):
  f=x-e*math.sin(x)-m
  if abs(f)<=5e-16:return x
  if f<0:lo=x
  else:hi=x
  n=x-f/(1-e*math.cos(x))
  x=n if lo<n<hi else (lo+hi)/2
 return x
def prepare(o):
 o.mkdir(parents=True,exist_ok=True);raw=Path('/app/input.json').read_bytes();cfg=json.loads(raw)
 assert cfg['eccentricities']==list(ES) and cfg['intervals']==N
 js(o/'manifest.json',{'workflow_version':V,'issue':54,'input_sha256':hashlib.sha256(raw).hexdigest(),'runtime':'Python 3.11.14 standard library, binary64, no RNG','source':'Johannes Kepler, Astronomia nova (1609)','licenses':{'code':'Apache-2.0','input':'CC0-1.0','historical_source':'public domain'}})
def orbit(o,e):
 q=tag(e);p=o/f'orbit-e{q}.csv';rows=[];areas=[];res=[];ell=[]
 for i in range(N+1):
  m=2*math.pi*i/N;E=solve_e(m,e);x=math.cos(E)-e;y=math.sqrt(1-e*e)*math.sin(E);r=1-e*math.cos(E)
  rows.append((i,m,E,x,y,r));res.append(abs(E-e*math.sin(E)-m));ell.append(abs((x+e)**2+y*y/(1-e*e)-1))
 for a,b in zip(rows,rows[1:]):
  # Exact parametric line integral over [E0,E1], independently evaluated from x dy-y dx.
  e0,e1=a[2],b[2];s=math.sqrt(1-e*e);de=e1-e0;areas.append(.5*s*(de-2*e*math.cos((e0+e1)/2)*math.sin(de/2)))
 with p.open('w',newline='') as f:
  w=csv.writer(f);w.writerow(('index','mean_anomaly','eccentric_anomaly','x','y','radius','swept_area_increment'));[w.writerow((*r,areas[i] if i<N else '')) for i,r in enumerate(rows)]
 quarter=tuple(rows[i][2] for i in (N//4,N//2,3*N//4));expected=math.pi*math.sqrt(1-e*e)/N
 velocities=[]
 dt=2*math.pi/N
 for i in range(2,N-1):
  xm=(rows[i-2][3]-8*rows[i-1][3]+8*rows[i+1][3]-rows[i+2][3])/(12*dt);ym=(rows[i-2][4]-8*rows[i-1][4]+8*rows[i+1][4]-rows[i+2][4])/(12*dt);velocities.append(.5*(rows[i][3]*ym-rows[i][4]*xm))
 js(o/f'metrics-e{q}.json',{'eccentricity':e,'max_solver_residual':max(res),'all_in_bracket':all(m-e-1e-15<=E<=m+e+1e-15 for _,m,E,*_ in rows),'quarter_anomalies':quarter,'max_quarter_error':max(abs(a-b) for a,b in zip(quarter,REF[e])),'max_ellipse_residual':max(ell),'periapsis':min(r[5] for r in rows),'apoapsis':max(r[5] for r in rows),'max_interval_area_relative_error':max(abs(a/expected-1) for a in areas),'total_area':sum(areas),'expected_total_area':math.pi*math.sqrt(1-e*e),'areal_velocity_relative_span':(max(velocities)-min(velocities))/(sum(velocities)/len(velocities))})
def aggregate(o):
 ms=[json.loads((o/f'metrics-e{tag(e)}.json').read_text()) for e in ES]
 js(o/'metrics.json',{'workflow_version':V,'branches':ms,'scientific_statement':'Uniform time increments sweep equal areas on ideal dimensionless Kepler ellipses.'})
def png(path,curves):
 W,H=900,560;pix=[bytearray(b'\xff'*(W*3)) for _ in range(H)]
 def line(x,y,u,v,c):
  dx=abs(u-x);sx=1 if x<u else -1;dy=-abs(v-y);sy=1 if y<v else -1;er=dx+dy
  while True:
   if 0<=x<W and 0<=y<H:pix[y][3*x:3*x+3]=bytes(c)
   if x==u and y==v:break
   z=2*er
   if z>=dy:er+=dy;x+=sx
   if z<=dx:er+=dx;y+=sy
 line(45,280,855,280,(30,30,30));line(450,35,450,525,(30,30,30));cols=((20,90,190),(20,150,100),(220,120,20),(190,40,50))
 for pts,c in zip(curves,cols):
  for p,q in zip(pts,pts[1:]):line(*p,*q,c)
 raw=b''.join(b'\0'+bytes(r) for r in pix)
 def ch(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
def render(o):
 curves=[];area=[]
 for e in ES:
  with (o/f'orbit-e{tag(e)}.csv').open() as f:r=list(csv.DictReader(f))
  curves.append([(450+round(float(x['x'])*360),280-round(float(x['y'])*230)) for x in r])
  vals=[float(x['swept_area_increment']) for x in r[:-1]];avg=sum(vals)/len(vals);area.append([(45+round(i/(N-1)*810),280-round((v/avg-1)*1e13)) for i,v in enumerate(vals)])
 png(o/'kepler-orbits.png',curves);png(o/'equal-area-law.png',area)
 # GIF: actual positions at 24 uniformly spaced times, all four eccentricities.
 W,H=480,300;pal=bytes((255,255,255,30,30,30,20,90,190,20,150,100,220,120,20,190,40,50,230,230,230,120,120,120));d=bytearray(b'GIF89a'+struct.pack('<HH',W,H)+b'\x82\x00\x00'+pal+b'\0'*(24-len(pal))+b'!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00')
 for frame in range(24):
  a=[0]*(W*H);m=2*math.pi*frame/24
  for ci,e in enumerate(ES,2):
   E=solve_e(m,e);x=240+round((math.cos(E)-e)*190);y=150-round(math.sqrt(1-e*e)*math.sin(E)*115)
   for q in range(101):a[round(150+(y-150)*q/100)*W+round(240+(x-240)*q/100)]=ci
   for yy in range(y-3,y+4):
    for xx in range(x-3,x+4):
     if 0<=xx<W and 0<=yy<H:a[yy*W+xx]=ci
  codes=[]
  for q in a:codes+=(8,q)
  codes+=[9];pk=bytearray();bits=nb=0
  for code in codes:
   bits|=code<<nb;nb+=4
   while nb>=8:pk.append(bits&255);bits>>=8;nb-=8
  if nb:pk.append(bits&255)
  d+=b'!\xf9\x04\x00\x0a\x00\x00\x00,'+struct.pack('<HHHH',0,0,W,H)+b'\x00\x03'
  for i in range(0,len(pk),255):d+=bytes([len(pk[i:i+255])])+pk[i:i+255]
  d+=b'\0'
 (o/'kepler-orbits.gif').write_bytes(d+b';')
def validate(o,reference=None):
 m=json.loads((o/'metrics.json').read_text());checks={}
 checks['solver']=all(x['max_solver_residual']<=2e-14 and x['all_in_bracket'] for x in m['branches']);checks['quarters']=all(x['max_quarter_error']<=3e-14 for x in m['branches']);checks['geometry']=all(x['max_ellipse_residual']<=2e-14 and abs(x['periapsis']-(1-x['eccentricity']))<=2e-14 and abs(x['apoapsis']-(1+x['eccentricity']))<=2e-14 for x in m['branches']);checks['areas']=all(x['max_interval_area_relative_error']<=5e-12 and abs(x['total_area']/x['expected_total_area']-1)<=2e-13 for x in m['branches']);checks['areal_velocity']=all(x['areal_velocity_relative_span']<=2e-5 for x in m['branches']);checks['media']=(o/'kepler-orbits.png').read_bytes().startswith(b'\x89PNG') and (o/'equal-area-law.png').read_bytes().startswith(b'\x89PNG') and (o/'kepler-orbits.gif').read_bytes().count(b'!\xf9')>1
 files=['manifest.json','metrics.json','kepler-orbits.png','equal-area-law.png','kepler-orbits.gif']+[f'orbit-e{tag(e)}.csv' for e in ES]+[f'metrics-e{tag(e)}.json' for e in ES]
 checks['byte_identical_reference']=reference is None or all((o/f).read_bytes()==(Path(reference)/f).read_bytes() for f in files)
 js(o/'validation.json',{'overall_pass':all(checks.values()),'checks':checks,'checksums':{f:hashlib.sha256((o/f).read_bytes()).hexdigest() for f in files},'limitations':['ideal dimensionless two-body orbit, not an observed Solar-System ephemeris','modern eccentric-anomaly notation applied to Kepler historical geometric laws','no perturbations, relativity, finite masses, or observational uncertainty']})
 if not all(checks.values()):raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--output',default='.');p.add_argument('--eccentricity',type=float);p.add_argument('--reference');a=p.parse_args();o=Path(a.output);{'prepare':lambda:prepare(o),'orbit':lambda:orbit(o,a.eccentricity),'aggregate':lambda:aggregate(o),'render':lambda:render(o),'validate':lambda:validate(o,a.reference)}[a.mode]()
if __name__=='__main__':main()
