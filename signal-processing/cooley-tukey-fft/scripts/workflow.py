#!/usr/bin/env python3
import argparse,csv,cmath,hashlib,json,math,struct,zlib
from pathlib import Path
V="community-cooley-tukey-fft-v1";N=1024;B=64;P=.37;OFF={"000":0.0,"0125":.125,"0250":.25,"0500":.5};AUD=(0,1,63,64,65,66,958,959,960,961,1023)
def dump(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n")
def fft(x,inv=False):
 a=list(x);j=0
 for i in range(1,N):
  q=N>>1
  while j&q:j^=q;q>>=1
  j^=q
  if i<j:a[i],a[j]=a[j],a[i]
 s=2
 while s<=N:
  w=cmath.exp((2j if inv else -2j)*math.pi/s)
  for i in range(0,N,s):
   u=1
   for k in range(i,i+s//2):v=a[k+s//2]*u;a[k],a[k+s//2]=a[k]+v,a[k]-v;u*=w
  s*=2
 return [z/N for z in a] if inv else a
def dft(x,k):return sum((v*cmath.exp(-2j*math.pi*k*n/N) for n,v in enumerate(x)),0j)
def geom(a):
 d=math.sin(math.pi*a/N)
 return complex(N) if abs(d)<1e-15 else cmath.exp(1j*math.pi*a*(N-1)/N)*math.sin(math.pi*a)/d
def analytic(f,k):return .5*cmath.exp(1j*P)*geom(f-k)+.5*cmath.exp(-1j*P)*geom(-(f+k))
def cp(z):return [float(format(z.real,'.17g')),float(format(z.imag,'.17g'))]
def prepare(o):o.mkdir(parents=True,exist_ok=True);dump(o/"scenario.json",{"version":V,"issue":40,"N":N,"base_bin":B,"phase":P,"offsets":OFF,"audit_bins":AUD,"window":"periodic Hann","license":"MIT"})
def audit(o,b):
 d=OFF[b];f=B+d;x=[math.cos(2*math.pi*f*n/N+P) for n in range(N)];w=[.5-.5*math.cos(2*math.pi*n/N) for n in range(N)];h=[a*q for a,q in zip(x,w)];X=fft(x);H=fft(h);xr=fft(X,True);hr=fft(H,True);tot=sum(abs(z)**2 for z in X);ht=sum(abs(z)**2 for z in H)
 def leak(a,keep,t):return sum(abs(z)**2 for k,z in enumerate(a) if k not in keep)/t
 m={"roundtrip_rect":max(abs(a-b) for a,b in zip(x,xr)),"roundtrip_hann":max(abs(a-b) for a,b in zip(h,hr)),"parseval_rect":abs(sum(q*q for q in x)-tot/N)/sum(q*q for q in x),"parseval_hann":abs(sum(q*q for q in h)-ht/N)/sum(q*q for q in h),"symmetry":max(max(abs(X[k]-X[-k].conjugate()),abs(H[k]-H[-k].conjugate())) for k in range(1,N)),"rect_nearest4":leak(X,{64,65,959,960},tot),"hann_nearest4":leak(H,{64,65,959,960},ht),"rect_exact":leak(X,{64,960},tot),"hann_exact":leak(H,{64,960},ht),"peak":max(range(N//2+1),key=lambda k:abs(X[k])),"mag64":abs(X[64]),"mag65":abs(X[65])}
 dump(o/f"audit-{b}.json",{"branch":b,"delta":d,"frequency":f,"samples":[format(q,'.17g') for q in x],"rect":[cp(z) for z in X],"hann":[cp(z) for z in H],"direct":{str(k):{"rect":cp(dft(x,k)),"hann":cp(dft(h,k))} for k in AUD},"metrics":m})
def aggregate(o):
 rows=[]
 for b,d in OFF.items():rows.append({"branch":b,"delta":d,**json.loads((o/f"audit-{b}.json").read_text())["metrics"]})
 dump(o/"aggregate.json",{"version":V,"rows":rows})
 with (o/"aggregate.csv").open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
def png(path,p):
 h=len(p);w=len(p[0])//3;raw=b"".join(b"\0"+bytes(r) for r in p)
 def ch(t,d):return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
 path.write_bytes(b"\x89PNG\r\n\x1a\n"+ch(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+ch(b"IDAT",zlib.compress(raw,9))+ch(b"IEND",b""))
def ln(p,x0,y0,x1,y1,c):
 dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
 while 1:
  if 0<=y0<len(p) and 0<=x0<len(p[0])//3:p[y0][3*x0:3*x0+3]=c
  if x0==x1 and y0==y1:return
  q=2*e
  if q>=dy:e+=dy;x0+=sx
  if q<=dx:e+=dx;y0+=sy
def gif(path,frames,w,h):
 d=bytearray(b"GIF89a"+struct.pack("<HH",w,h)+b"\x81\x00\x00"+bytes((255,255,255,20,20,20,35,95,190,205,35,45))+b"!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00")
 for fr in frames:
  c=[]
  for v in fr:c.extend((4,v))
  c.append(5);q=bytearray(c[i]|((c[i+1] if i+1<len(c) else 0)<<3) for i in range(0,len(c),2));d+=b"!\xf9\x04\x00\x28\x00\x00\x00,"+struct.pack("<HHHH",0,0,w,h)+b"\x00\x02"
  for i in range(0,len(q),255):d+=bytes((len(q[i:i+255]),))+q[i:i+255]
  d+=b"\0"
 path.write_bytes(d+b";")
def render(o):
 zs=[json.loads((o/f"audit-{b}.json").read_text()) for b in OFF];p=[[255]*2400 for _ in range(650)]
 for r,z in enumerate(zs):
  y=25+r*150;ln(p,50,y+115,780,y+115,(20,20,20));ln(p,50,y,50,y+115,(20,20,20))
  for key,col in (("rect",(35,95,190)),("hann",(205,35,45))):
   vs=[20*math.log10(max(1e-14,abs(complex(*z[key][k])))/(N/2)) for k in range(129)];pts=[(50+round(k*730/128),y+round(min(115,max(0,-v)))) for k,v in enumerate(vs)]
   for a,b in zip(pts,pts[1:]):ln(p,*a,*b,col)
 png(o/"spectral-leakage.png",p);frames=[]
 for upto in range(1,5):
  fr=[0]*(480*280)
  def gl(a,b,c,d,v):
   dx=abs(c-a);sx=1 if a<c else -1;dy=-abs(d-b);sy=1 if b<d else -1;e=dx+dy
   while 1:
    if 0<=a<480 and 0<=b<280:fr[b*480+a]=v
    if a==c and b==d:return
    q=2*e
    if q>=dy:e+=dy;a+=sx
    if q<=dx:e+=dx;b+=sy
  gl(30,250,460,250,1);gl(30,10,30,250,1)
  for i,z in enumerate(zs[:upto]):
   vs=[20*math.log10(max(1e-14,abs(complex(*z["rect"][k])))/(N/2)) for k in range(129)];pts=[(30+round(k*430/128),250-round((max(-100,v)+100)*2.3)) for k,v in enumerate(vs)]
   for a,b in zip(pts,pts[1:]):gl(*a,*b,2+i%2)
  frames.append(fr)
 gif(o/"leakage-offsets.gif",frames,480,280)
def validate(o,ref=None):
 checks=[]
 for b,d in OFF.items():
  z=json.loads((o/f"audit-{b}.json").read_text());m=z["metrics"];X=[complex(*q) for q in z["rect"]];H=[complex(*q) for q in z["hann"]]
  direct=all(abs(complex(*z["direct"][str(k)][kind])-a[k])<=2e-10*max(1,abs(complex(*z["direct"][str(k)][kind]))) for k in AUD for kind,a in (("rect",X),("hann",H)));base=max(m["roundtrip_rect"],m["roundtrip_hann"],m["parseval_rect"],m["parseval_hann"])<=2e-12 and m["symmetry"]<=2e-10*max(1,max(map(abs,X+H))) and direct;center=d!=0 or (m["rect_exact"]<=2e-24 and abs(m["mag64"]-512)/512<=2e-12);peak=m["peak"]==(65 if d==.5 else 64);phase=True
  if d==.5:
   phase=all(abs(complex(*z["direct"][str(k)]["rect"])-analytic(64.5,k))<=2e-12*max(1,abs(analytic(64.5,k))) for k in (64,65));gap=lambda a:(abs(a[65])-abs(a[64]))/abs(a[65]);phase=phase and abs(gap({k:complex(*z["direct"][str(k)]["rect"]) for k in (64,65)})-gap({k:analytic(64.5,k) for k in (64,65)}))<=2e-12
  checks.append({"branch":b,"pass":bool(base and center and peak and phase and (d==0 or m["rect_exact"]>1e-8)),"direct_dft":direct,"analytic_half_bin":phase})
 w=[.5-.5*math.cos(2*math.pi*n/N) for n in range(N)];hann=w[0]==0 and abs(w[512]-1)<=2e-15 and max(abs(w[n]-w[N-n]) for n in range(1,N))<=2e-15 and abs(sum(w)-512)<=2e-12;files=["scenario.json","aggregate.json","aggregate.csv","spectral-leakage.png","leakage-offsets.gif"]+[f"audit-{b}.json" for b in OFF];sums={f:hashlib.sha256((o/f).read_bytes()).hexdigest() for f in files};det=ref is None or all((o/f).read_bytes()==(Path(ref)/f).read_bytes() for f in files);ok=all(q["pass"] for q in checks) and hann and det;dump(o/"validation.json",{"overall_pass":ok,"branches":checks,"hann_invariants":hann,"deterministic_reference":det,"checksums":sums,"limitations":["finite sampled-record numerical audit, not a proof of Fourier theory or an analog measurement","window leakage comparison is scenario-specific, not a universal theorem"]})
 if not ok:raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument("mode",choices=("prepare","audit","aggregate","render","validate"));p.add_argument("--output",default=".");p.add_argument("--branch");p.add_argument("--reference");a=p.parse_args();o=Path(a.output);{"prepare":lambda:prepare(o),"audit":lambda:audit(o,a.branch),"aggregate":lambda:aggregate(o),"render":lambda:render(o),"validate":lambda:validate(o,a.reference)}[a.mode]()
if __name__=="__main__":main()
