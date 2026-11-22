#!/usr/bin/env python3
import argparse, csv, hashlib, json, math, random, struct, zlib
from pathlib import Path

VERSION="community-buffon-needle-v1"; N=2_000_000
CHECKPOINTS=(100,300,1000,3000,10000,30000,100000,300000,1000000,2000000)
BRANCHES={f"seed-{i}":2026112300+i for i in range(1,5)}

def dump(path,obj): Path(path).write_text(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n")
def prepare(out):
 out.mkdir(parents=True,exist_ok=True); dump(out/"scenario.json",{"workflow_version":VERSION,"issue":38,"law":"p=2L/(pi*d)","L":1,"d":1,"exact_probability":2/math.pi,"trials_per_branch":N,"seeds":BRANCHES,"draw_order":["midpoint_distance","acute_angle"],"prng":"Python 3.11 random.Random (MT19937)","checkpoints":CHECKPOINTS})
def sample(out,branch):
 seed=BRANCHES[branch]; rng=random.Random(seed); crossings=0; sx=st=0.0; cps=[]; raw=[]
 for i in range(1,N+1):
  x=.5*rng.random(); theta=(math.pi/2)*rng.random(); crossed=x<=.5*math.sin(theta); crossings+=crossed; sx+=x; st+=theta
  if i<=1000: raw.append((i,format(x,'.17g'),format(theta,'.17g'),int(crossed)))
  if i in CHECKPOINTS: cps.append({"trials":i,"crossings":crossings})
 fields=("branch","seed","trials","crossings","midpoint_sum","angle_sum")
 with (out/f"summary-{branch}.csv").open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerow(dict(zip(fields,(branch,seed,N,crossings,format(sx,'.17g'),format(st,'.17g')))))
 with (out/f"raw-{branch}.csv").open("w",newline="") as f: w=csv.writer(f); w.writerow(("toss","midpoint_distance","angle_radians","crossed")); w.writerows(raw)
 dump(out/f"checkpoints-{branch}.json",{"branch":branch,"seed":seed,"checkpoints":cps})
def rows(out):
 result=[]
 for b in BRANCHES:
  with (out/f"summary-{b}.csv").open() as f: result.append(next(csv.DictReader(f)))
 return result
def aggregate(out):
 rr=rows(out); total=sum(int(r["crossings"]) for r in rr); n=4*N; p=total/n; exact=2/math.pi; se=math.sqrt(exact*(1-exact)/n); pi_hat=2/p; pi_se=(2/exact**2)*se
 cps={b:json.loads((out/f"checkpoints-{b}.json").read_text())["checkpoints"] for b in BRANCHES}; conv=[]
 for j,k in enumerate(CHECKPOINTS):
  c=sum(cps[b][j]["crossings"] for b in BRANCHES); ph=c/(4*k); conv.append({"trials_per_branch":k,"crossings":c,"trials":4*k,"probability":ph,"pi_hat":2/ph})
 dispersion=sum((int(r["crossings"])-N*exact)**2/(N*exact*(1-exact)) for r in rr)
 metrics={"workflow_version":VERSION,"total_trials":n,"total_crossings":total,"exact_probability":exact,"probability":p,"probability_standard_error":se,"probability_absolute_error":abs(p-exact),"pi_hat":pi_hat,"pi_standard_error_delta":pi_se,"pi_absolute_error":abs(pi_hat-math.pi),"pearson_dispersion":dispersion,"convergence":conv}
 dump(out/"aggregate.json",metrics)
 with (out/"aggregate.csv").open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=[k for k in metrics if k!="convergence"]); w.writeheader(); w.writerow({k:v for k,v in metrics.items() if k!="convergence"})
def png(path,pix):
 h=len(pix); w=len(pix[0])//3; raw=b"".join(b"\0"+bytes(r) for r in pix)
 def chunk(t,d): return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
 path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))
def line(p,x0,y0,x1,y1,c,width=1):
 dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; e=dx+dy
 while True:
  for ox in range(-width,width+1):
   for oy in range(-width,width+1):
    x=x0+ox;y=y0+oy
    if 0<=y<len(p) and 0<=x<len(p[0])//3:p[y][3*x:3*x+3]=c
  if x0==x1 and y0==y1:break
  q=2*e
  if q>=dy:e+=dy;x0+=sx
  if q<=dx:e+=dx;y0+=sy
def render(out):
 p=[[255]*2400 for _ in range(600)]
 for y in (100,300,500): line(p,20,y,780,y,(20,20,20),1)
 for bi,b in enumerate(BRANCHES):
  with (out/f"raw-{b}.csv").open() as f: rr=list(csv.DictReader(f))[:250]
  for j,r in enumerate(rr):
   x=30+(j%50)*15; base=100+((j//50+bi)%3)*200; t=float(r["angle_radians"]); d=float(r["midpoint_distance"]); cy=base+round((d if j%2 else -d)*180); dx=round(math.cos(t)*7);dy=round(math.sin(t)*90); line(p,x-dx,cy-dy,x+dx,cy+dy,(205,35,45) if r["crossed"]=="1" else (35,95,190),1)
 png(out/"needle-geometry.png",p)
 # A deterministic animated convergence strip; each frame is a standards-compliant single-image GIF.
 conv=json.loads((out/"aggregate.json").read_text())["convergence"]
 frames=[]
 for upto in range(1,len(conv)+1):
  idx=[0]*(640*360)
  def gl(x0,y0,x1,y1,c):
   dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
   while True:
    if 0<=x0<640 and 0<=y0<360:idx[y0*640+x0]=c
    if x0==x1 and y0==y1:break
    q=2*e
    if q>=dy:e+=dy;x0+=sx
    if q<=dx:e+=dx;y0+=sy
  gl(40,320,610,320,1); gl(40,20,40,320,1); pts=[]
  for i,v in enumerate(conv[:upto]): pts.append((40+round(i*570/(len(conv)-1)),round(170-(v["probability"]-2/math.pi)*12000)))
  for a,b in zip(pts,pts[1:]):gl(*a,*b,2)
  frames.append(idx)
 gif(out/"convergence.gif",frames,640,360)
def gif(path,frames,w,h):
 # Uncompressed literal stream with clear codes between pixels keeps encoding simple and reproducible.
 data=bytearray(b"GIF89a"+struct.pack("<HH",w,h)+b"\x81\x00\x00"+bytes((255,255,255,20,20,20,35,95,190,205,35,45)))
 data+=b"!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
 for frame in frames:
  codes=[]
  for v in frame: codes.extend((4,v))
  codes.append(5); packed=bytearray()
  for i in range(0,len(codes),2): packed.append(codes[i]|((codes[i+1] if i+1<len(codes) else 0)<<3))
  data+=b"!\xf9\x04\x00\x0c\x00\x00\x00,"+struct.pack("<HHHH",0,0,w,h)+b"\x00\x02"
  for i in range(0,len(packed),255):data+=bytes((len(packed[i:i+255]),))+packed[i:i+255]
  data+=b"\x00"
 data+=b";";path.write_bytes(data)
def validate(out,reference=None):
 exact=2/math.pi; rr=rows(out); checks=[]
 for b,r in zip(BRANCHES,rr):
  n=int(r["trials"]); c=int(r["crossings"]); se=math.sqrt(exact*(1-exact)/n); raw=list(csv.DictReader((out/f"raw-{b}.csv").open())); cp=json.loads((out/f"checkpoints-{b}.json").read_text())["checkpoints"]
  raw_ok=len(raw)==1000 and all(0<=float(x["midpoint_distance"])<.5 and 0<=float(x["angle_radians"])<math.pi/2 and int(x["crossed"])==int(float(x["midpoint_distance"])<=.5*math.sin(float(x["angle_radians"]))) for x in raw)
  meanx=float(r["midpoint_sum"])/n; meant=float(r["angle_sum"])/n
  checks.append({"branch":b,"pass":n==N and int(r["seed"])==BRANCHES[b] and abs(c/n-exact)<=5*se and abs(meanx-.25)<=5*(.5/math.sqrt(12*n)) and abs(meant-math.pi/4)<=5*((math.pi/2)/math.sqrt(12*n)) and raw_ok and cp[-1]=={"trials":N,"crossings":c}})
 m=json.loads((out/"aggregate.json").read_text()); files=["scenario.json","aggregate.json","aggregate.csv","needle-geometry.png","convergence.gif"]+[f"{x}-{b}.{e}" for b in BRANCHES for x,e in (("summary","csv"),("raw","csv"),("checkpoints","json"))]
 sums={f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in files}; deterministic=reference is None or all((out/f).read_bytes()==(Path(reference)/f).read_bytes() for f in files)
 overall=all(x["pass"] for x in checks) and m["probability_absolute_error"]<=5*m["probability_standard_error"] and m["pi_absolute_error"]<=5*m["pi_standard_error_delta"] and .01<=m["pearson_dispersion"]<=20 and deterministic
 dump(out/"validation.json",{"overall_pass":overall,"branches":checks,"pooled_probability_pass":m["probability_absolute_error"]<=5*m["probability_standard_error"],"pi_pass":m["pi_absolute_error"]<=5*m["pi_standard_error_delta"],"dispersion_pass":.01<=m["pearson_dispersion"]<=20,"deterministic_reference_pass":deterministic,"checksums":sums,"limitations":["deterministic pseudorandom numerical audit, not a physical experiment","MT19937 is not cryptographic","inverse pi estimator is nonlinear","statistically inefficient for computing pi"]})
 if not overall:raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument("mode",choices=("prepare","sample","aggregate","render","validate"));p.add_argument("--output",default=".");p.add_argument("--branch");p.add_argument("--reference");a=p.parse_args();o=Path(a.output);{"prepare":lambda:prepare(o),"sample":lambda:sample(o,a.branch),"aggregate":lambda:aggregate(o),"render":lambda:render(o),"validate":lambda:validate(o,a.reference)}[a.mode]()
if __name__=="__main__":main()
