#!/usr/bin/env python3
import argparse,csv,hashlib,json,math,struct,zlib
from decimal import Decimal,localcontext
from pathlib import Path

VERSION="community-airy-diffraction-v1"
WAVELENGTHS={"450nm":450,"550nm":550,"650nm":650}
ROOT_REF=3.831705970207512
def dump(p,o): Path(p).write_text(json.dumps(o,sort_keys=True,separators=(",",":"))+"\n")
def bessel(order,x):
 with localcontext() as c:
  c.prec=80;x=x if isinstance(x,Decimal) else Decimal(str(x));q=-(x*x)/4
  term=Decimal(1) if order==0 else x/2; total=term;k=0
  while True:
   k+=1;term*=q/(Decimal(k*k) if order==0 else Decimal(k*(k+1)));total+=term
   if abs(term)<Decimal('1e-70'):return +total,k
   if k>=10000:raise RuntimeError('Bessel series cap')
def values(u):
 j0,i0=bessel(0,u);j1,i1=bessel(1,u);i=Decimal(1) if not u else (2*j1/u)**2;e=1-j0*j0-j1*j1
 return j0,j1,i,e,max(i0,i1)
def root():
 lo=Decimal('3.8');hi=Decimal('3.9')
 while hi-lo>Decimal('2e-15'):
  mid=(lo+hi)/2
  if bessel(1,mid)[0]>0:lo=mid
  else:hi=mid
 return (lo+hi)/2
def integrand(x):
 if x==0:return 0.0
 j=float(bessel(1,x)[0]);return 2*j*j/x
def simpson(end,n):
 h=end/n;s=integrand(0.0)+integrand(end)
 for i in range(1,n):s+=(4 if i%2 else 2)*integrand(i*h)
 return s*h/3
def png(path,w,h,rows):
 raw=b''.join(b'\0'+bytes(r) for r in rows)
 def ch(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
def line(p,w,x0,y0,x1,y1,c):
 dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
 while True:
  if 0<=x0<w and 0<=y0<len(p):p[y0][3*x0:3*x0+3]=c
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
  d+=b'!\xf9\x04\x00\x08\x00\x00\x00,'+struct.pack('<HHHH',0,0,w,h)+b'\x00\x02'
  for i in range(0,len(packed),255):d+=bytes((len(packed[i:i+255]),))+packed[i:i+255]
  d+=b'\x00'
 d+=b';';path.write_bytes(d)
def prepare(out):
 out.mkdir(parents=True,exist_ok=True);dump(out/'manifest.json',{'workflow_version':VERSION,'issue':37,'diameter_m':0.1,'focal_length_m':1.0,'wavelength_nm':list(WAVELENGTHS.values()),'grid':{'u_min':0,'u_max':20,'step':0.001,'samples':20001},'decimal_precision':80,'series_term_threshold':'1e-70','root_bracket':[3.8,3.9],'quadrature_subintervals':131072,'source':'George Biddell Airy (1835); NIST DLMF 10.21 and 10.22','runtime':'Python 3.11.14 standard library; no RNG'})
def evaluate(out,name):
 nm=WAVELENGTHS[name];wl=Decimal(nm)*Decimal('1e-9');r=root();rows=[];maxit=0
 for n in range(20001):
  u=Decimal(n)/1000;j0,j1,intensity,energy,it=values(u);maxit=max(maxit,it);radius=u*wl/(Decimal(str(math.pi))*Decimal('0.1'))
  rows.append((n,str(u),format(radius,'.17E'),format(j0,'.17E'),format(j1,'.17E'),format(intensity,'.17E'),format(energy,'.17E')))
 with (out/f'{name}.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(('sample','u','radius_m','j0','j1','intensity','encircled_energy'));w.writerows(rows)
 rf=float(r);j0,j1,_,energy,_=values(r);q=simpson(rf,131072)
 checks={str(x):simpson(float(x),8192) for x in (1,2,3,ROOT_REF,5,10,20)}
 dump(out/f'{name}-summary.json',{'wavelength_nm':nm,'root_u':rf,'j1_at_root':float(j1),'dark_radius_m':float(r*wl/(Decimal(str(math.pi))*Decimal('0.1'))),'energy_at_root':float(energy),'quadrature_at_root':q,'checkpoint_integrals':checks,'max_series_iterations':maxit})
 vals=[float(x[5]) for x in rows];size=1024;pix=[];scale=8/(size-1)
 for y in range(size):
  row=[];yy=-4+y*scale
  for x in range(size):
   uu=math.pi*math.hypot(-4+x*scale,yy);idx=min(20000,round(uu*1000));v=max(0,min(255,round(255*math.sqrt(vals[idx]))));row.extend((v,v,v))
  pix.append(row)
 png(out/f'{name}-psf.png',size,size,pix)
def readcsv(p):
 with p.open() as f:return list(csv.DictReader(f))
def aggregate(out):
 summaries={k:json.loads((out/f'{k}-summary.json').read_text()) for k in WAVELENGTHS};base=readcsv(out/'450nm.csv');identity=True
 for k in ('550nm','650nm'):
  other=readcsv(out/f'{k}.csv');identity &= all(a['intensity']==b['intensity'] and a['encircled_energy']==b['encircled_energy'] for a,b in zip(base,other))
 dump(out/'summary.json',{'workflow_version':VERSION,'branches':summaries,'dimensionless_columns_identical':identity,'radius_ratios':{'450/550':summaries['450nm']['dark_radius_m']/summaries['550nm']['dark_radius_m'],'550/650':summaries['550nm']['dark_radius_m']/summaries['650nm']['dark_radius_m']}})
def render(out):
 w=960;h=540;p=[[255]*(w*3) for _ in range(h)];line(p,w,50,480,920,480,(20,20,20));line(p,w,50,30,50,480,(20,20,20));colors=((35,95,190),(40,150,80),(205,35,45))
 for c,name in zip(colors,WAVELENGTHS):
  rows=readcsv(out/f'{name}.csv');pts=[(50+round(float(r['u'])/20*870),480-round(float(r['encircled_energy'])*420)) for r in rows]
  for a,b in zip(pts,pts[1:]):line(p,w,*a,*b,c)
 png(out/'airy-profiles.png',w,h,p)
 frames=[]
 for nm in range(450,651,10):
  fr=[];scale=8/319
  for y in range(180):
   yy=(-90+y)*scale
   for x in range(320):
    u=math.pi*math.hypot((-160+x)*scale,yy);j=float(bessel(1,u)[0]);v=1 if u==0 else (2*j/u)**2;fr.append(1 if v<.01 else 2 if v<.15 else 3)
  frames.append(fr)
 gif(out/'wavelength-sweep.gif',frames,320,180)
def validate(out,reference=None):
 summary=json.loads((out/'summary.json').read_text());checks={}
 for name,nm in WAVELENGTHS.items():
  rows=readcsv(out/f'{name}.csv');s=summary['branches'][name];e=[float(r['encircled_energy']) for r in rows];ints=[float(r['intensity']) for r in rows]
  checkpoints=s['checkpoint_integrals'];analytic={str(x):float(values(Decimal(str(x)))[3]) for x in (1,2,3,ROOT_REF,5,10,20)}
  checks[name]=len(rows)==20001 and all(math.isfinite(float(v)) for r in rows for v in r.values()) and min(ints)>=0 and min(b-a for a,b in zip(e,e[1:]))>=-2e-14 and abs(s['root_u']-ROOT_REF)<=2e-14 and abs(s['j1_at_root'])<=2e-15 and s['max_series_iterations']<10000 and abs(s['energy_at_root']-s['quadrature_at_root'])<=2e-10 and all(abs(checkpoints[str(x)]-analytic[str(x)])<=2e-9 for x in (1,2,3,ROOT_REF,5,10,20))
 checks['identity']=summary['dimensionless_columns_identical'];checks['ratios']=abs(summary['radius_ratios']['450/550']-450/550)<=2e-14 and abs(summary['radius_ratios']['550/650']-550/650)<=2e-14
 files=['manifest.json','450nm.csv','550nm.csv','650nm.csv','450nm-summary.json','550nm-summary.json','650nm-summary.json','450nm-psf.png','550nm-psf.png','650nm-psf.png','summary.json','airy-profiles.png','wavelength-sweep.gif'];checks['files']=all((out/f).exists() and (out/f).stat().st_size>0 for f in files);checks['determinism']=reference is None or all((out/f).read_bytes()==(Path(reference)/f).read_bytes() for f in files)
 dump(out/'validation.json',{'passed':all(checks.values()),'checks':checks,'limitations':'Ideal scalar monochromatic paraxial unobscured aperture; not a measured telescope PSF.'})
 if not all(checks.values()):raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','evaluate','aggregate','render','validate'));p.add_argument('--output',default='.');p.add_argument('--branch');p.add_argument('--reference');a=p.parse_args();o=Path(a.output);{'prepare':lambda:prepare(o),'evaluate':lambda:evaluate(o,a.branch),'aggregate':lambda:aggregate(o),'render':lambda:render(o),'validate':lambda:validate(o,a.reference)}[a.mode]()
if __name__=='__main__':main()
