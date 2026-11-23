#!/usr/bin/env python3
import argparse,csv,hashlib,json,math,struct,zlib
from pathlib import Path
V='community-planck-blackbody-v4'; TEMPS=(300,1000,3000,5778)
def js(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
def load():return json.loads(Path('/app/input.json').read_text())
def root():
 lo,hi=4.,6.
 for _ in range(100):
  m=(lo+hi)/2
  if 5*(1-math.exp(-m))-m>0:lo=m
  else:hi=m
 return (lo+hi)/2
def f(x):return x**3/math.expm1(x) if x else 0.
def simpson(n=200000,hi=50.):
 d=hi/n;s=f(0)+f(hi)+4*sum(f(i*d) for i in range(1,n,2))+2*sum(f(i*d) for i in range(2,n,2));return s*d/3
def constants():
 a=load()['constants'];h=a['h_j_s'];c=a['c_m_s'];k=a['k_b_j_k'];x=root();return h,c,k,x,h*c/k/x,2*math.pi**5*k**4/(15*h**3*c**2)
def prep(o):
 o.mkdir(parents=True,exist_ok=True);h,c,k,x,b,s=constants();cfg=load()['quadrature'];q=simpson(cfg['oracle_panels'],cfg['dimensionless_x_max']);js(o/'manifest.json',{'workflow_version':V,'issue':53,'input_sha256':hashlib.sha256(Path('/app/input.json').read_bytes()).hexdigest(),'runtime':'Python 3.11.14 standard library, binary64, no RNG','paper_doi':'10.1002/andp.19013090310','licenses':{'code':'Apache-2.0','input':'CC0-1.0'}});js(o/'oracle.json',{'peak_root':x,'peak_residual':5*(1-math.exp(-x))-x,'wien_m_k':b,'stefan_boltzmann_w_m2_k4':s,'dimensionless_integral':q,'integral_oracle':math.pi**4/15})
def solve(o,t):
 h,c,k,x,b,s=constants();n=1201;xs=[.05+i*(49.95/(n-1)) for i in range(n)];rows=[]
 for v in reversed(xs):
  lam=h*c/(k*t*v);m=2*math.pi*h*c*c/lam**5/math.expm1(v);rows.append((lam,m));
 rows.sort();p=o/f'spectrum-{t}.csv'
 with p.open('w',newline='') as z:w=csv.writer(z);w.writerow(('wavelength_m','spectral_exitance_w_m3'));w.writerows(rows)
 # Independently solve the stationary-point equation for every branch.
 lo,hi=4.,6.
 for _ in range(100):
  mid=(lo+hi)/2
  if 5*(1-math.exp(-mid))-mid>0:lo=mid
  else:hi=mid
 peak=h*c/(k*t*((lo+hi)/2));cfg=load()['quadrature'];panels=cfg['branch_panels'];xmax=cfg['dimensionless_x_max'];q=simpson(panels,xmax);tail=math.exp(-xmax)*(xmax**3+3*xmax**2+6*xmax+6);flux=(2*math.pi*(k*t)**4/(h**3*c**2))*q;js(o/f'metrics-{t}.json',{'temperature_k':t,'quadrature_panels':panels,'dimensionless_bounds':[0,xmax],'positive_strictly_increasing_grid':all(rows[i][0]>0 and rows[i][0]<rows[i+1][0] and math.isfinite(rows[i][1]) for i in range(len(rows)-1)),'omitted_dimensionless_tail_bound':tail,'numerical_peak_m':peak,'analytic_peak_m':b/t,'peak_product_m_k':peak*t,'numerical_flux_w_m2':flux,'analytic_flux_w_m2':s*t**4,'dimensionless_integral':q})
def aggregate(o):
 r=[json.loads((o/f'metrics-{t}.json').read_text()) for t in TEMPS];lx=[math.log(x['temperature_k']) for x in r];ly=[math.log(x['numerical_flux_w_m2']) for x in r];a=sum(lx)/4;b=sum(ly)/4;slope=sum((x-a)*(y-b) for x,y in zip(lx,ly))/sum((x-a)**2 for x in lx);js(o/'metrics.json',{'workflow_version':V,'temperatures':r,'flux_log_slope':slope,'peak_product_relative_span':(max(x['peak_product_m_k'] for x in r)-min(x['peak_product_m_k'] for x in r))/(sum(x['peak_product_m_k'] for x in r)/4)})
def png(p,curves,markers=()):
 W,H=900,560;a=[[255]*(W*3) for _ in range(H)]
 def line(x,y,u,v,c):
  dx=abs(u-x);sx=1 if x<u else -1;dy=-abs(v-y);sy=1 if y<v else -1;e=dx+dy
  while True:
   if 0<=x<W and 0<=y<H:a[y][3*x:3*x+3]=c
   if x==u and y==v:break
   z=2*e
   if z>=dy:e+=dy;x+=sx
   if z<=dx:e+=dx;y+=sy
 line(55,500,870,500,(20,20,20));line(55,35,55,500,(20,20,20));colors=((30,100,190),(20,150,100),(220,120,20),(190,40,50))
 for pts,col in zip(curves,colors):
  for p1,p2 in zip(pts,pts[1:]):line(*p1,*p2,col)
 for x,y,col in markers:
  line(x-5,y,x+5,y,col);line(x,y-5,x,y+5,col)
 raw=b''.join(b'\0'+bytes(r) for r in a)
 def ch(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 p.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
def render(o):
 curves=[]
 for t in TEMPS:
  with (o/f'spectrum-{t}.csv').open() as f:r=list(csv.DictReader(f));vals=[(float(x['wavelength_m'])*1e6,float(x['spectral_exitance_w_m3'])) for x in r];m=max(y for x,y in vals);curves.append([(55+round((math.log10(x)+1.4)/2.2*815),500-round(y/m*430)) for x,y in vals if .04<=x<=6.3])
 png(o/'planck-spectra.png',curves)
 metrics=json.loads((o/'metrics.json').read_text())['temperatures'];law_curves=[];markers=[]
 # Left half: normalized Wien product. Right half: flux divided by sigma*T^4.
 for j,key in enumerate(('peak_product_m_k','numerical_flux_w_m2')):
  vals=[]
  for i,r in enumerate(metrics):
   ratio=r[key]/((constants()[4]) if j==0 else r['analytic_flux_w_m2']);x=110+j*405+i*95;y=270-round((ratio-0.999998)*100000000);vals.append((x,max(60,min(480,y))));markers.append((x,max(60,min(480,y)),((30,100,190),(190,40,50))[j]))
  law_curves.append(vals)
 png(o/'radiation-laws.png',law_curves,markers)
 d=bytearray(b'GIF89a'+struct.pack('<HH',320,180)+b'\x81\x00\x00'+bytes((255,255,255,20,20,20,30,100,190,190,40,50))+b'!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00')
 for frame in range(12):
  pix=[0]*(320*180);t=300+(5778-300)*frame/11;h,c,k,x,b,s=constants();peak=b/t;values=[]
  for px in range(12,312):
   lam=10**(-1.4+2.2*(px-12)/299)*1e-6;v=h*c/(lam*k*t);m=0. if v>700 else 2*math.pi*h*c*c/lam**5/math.expm1(v);values.append((px,m))
  scale=max(v for _,v in values)
  for (x1,v1),(x2,v2) in zip(values,values[1:]):
   y1=165-round(v1/scale*145);y2=165-round(v2/scale*145);steps=max(abs(x2-x1),abs(y2-y1),1)
   for q in range(steps+1):pix[round(y1+(y2-y1)*q/steps)*320+round(x1+(x2-x1)*q/steps)]=2
  px=max(12,min(311,round(12+(math.log10(peak*1e6)+1.4)/2.2*299)))
  for y in range(20,166):pix[y*320+px]=3
  for x in range(12,312):pix[165*320+x]=1
  codes=[]
  for q in pix:codes+=(4,q)
  codes+=[5];pk=bytearray();bits=0;nbits=0
  for code in codes:
   bits|=code<<nbits;nbits+=3
   while nbits>=8:pk.append(bits&255);bits>>=8;nbits-=8
  if nbits:pk.append(bits&255)
  d+=b'!\xf9\x04\x00\x08\x00\x00\x00,'+struct.pack('<HHHH',0,0,320,180)+b'\x00\x02'
  for i in range(0,len(pk),255):d+=bytes([len(pk[i:i+255])])+pk[i:i+255]
  d+=b'\0'
 d+=b';';(o/'temperature-spectrum.gif').write_bytes(d)
def validate(o,ref=None):
 q=json.loads((o/'oracle.json').read_text());m=json.loads((o/'metrics.json').read_text())
 ch={'root':abs(q['peak_root']-4.965114231744277)<=2e-14 and abs(q['peak_residual'])<=2e-14,
     'wien':abs(q['wien_m_k']/2.8977719551851722e-3-1)<=5e-12,
     'integral':abs(q['dimensionless_integral']/(math.pi**4/15)-1)<=2e-10,
     'sigma':abs(q['stefan_boltzmann_w_m2_k4']/5.670374419e-8-1)<=5e-10,
     'peaks':all(abs(x['numerical_peak_m']/x['analytic_peak_m']-1)<=2e-7 for x in m['temperatures']),
     'flux':all(abs(x['numerical_flux_w_m2']/x['analytic_flux_w_m2']-1)<=2e-6 for x in m['temperatures']),
     'grid_and_tail':all(x['positive_strictly_increasing_grid'] and x['omitted_dimensionless_tail_bound']<1e-16 for x in m['temperatures']),
     'laws':abs(m['flux_log_slope']-4)<=2e-6 and m['peak_product_relative_span']<=2e-7,
     'media':(o/'planck-spectra.png').read_bytes().startswith(b'\x89PNG') and (o/'radiation-laws.png').read_bytes()!=(o/'planck-spectra.png').read_bytes() and (o/'temperature-spectrum.gif').read_bytes().count(b'!\xf9')>1}
 files=['manifest.json','oracle.json','metrics.json','planck-spectra.png','radiation-laws.png','temperature-spectrum.gif']+[f'spectrum-{t}.csv' for t in TEMPS]+[f'metrics-{t}.json' for t in TEMPS]
 ch['byte_identical_reference']=ref is None or all((o/f).read_bytes()==(Path(ref)/f).read_bytes() for f in files)
 js(o/'validation.json',{'overall_pass':all(ch.values()),'checks':ch,'checksums':{f:hashlib.sha256((o/f).read_bytes()).hexdigest() for f in files},'limitations':['ideal equilibrium blackbody, not measured material or stellar spectra','wavelength-domain peak is not the frequency-domain peak']})
 if not all(ch.values()):raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--output',default='.');p.add_argument('--temperature',type=int);p.add_argument('--reference');a=p.parse_args();o=Path(a.output);{'prepare':lambda:prep(o),'solve':lambda:solve(o,a.temperature),'aggregate':lambda:aggregate(o),'render':lambda:render(o),'validate':lambda:validate(o,a.reference)}[a.mode]()
if __name__=='__main__':main()
