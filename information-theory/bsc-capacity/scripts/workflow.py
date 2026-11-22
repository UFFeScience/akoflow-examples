#!/usr/bin/env python3
import argparse, csv, hashlib, json, math, random, struct, zlib
from pathlib import Path

VERSION="community-bsc-capacity-v1"; N=2_000_000
CHECKPOINTS=(100,300,1000,3000,10000,30000,100000,300000,1000000,2000000)
BRANCHES={"q001":(.01,2026112301),"q005":(.05,2026112302),"q010":(.10,2026112303),"q020":(.20,2026112304)}
def dump(p,o): Path(p).write_text(json.dumps(o,sort_keys=True,separators=(",",":"))+"\n")
def h2(q): return 0.0 if q in (0,1) else -q*math.log2(q)-(1-q)*math.log2(1-q)
def mi(c):
 n=sum(c); rows=(c[0]+c[1],c[2]+c[3]); cols=(c[0]+c[2],c[1]+c[3]); v=0.0
 for i,x in enumerate(c):
  if x: v+=(x/n)*math.log2(x*n/(rows[i//2]*cols[i%2]))
 return v
def prepare(out):
 out.mkdir(parents=True,exist_ok=True); dump(out/"scenario.json",{"workflow_version":VERSION,"issue":39,"law":"C(q)=1-H2(q)","trials_per_branch":N,"branches":{b:{"q":q,"seed":s} for b,(q,s) in BRANCHES.items()},"draw_order":["input_bit_getrandbits","flip_random"],"prng":"Python 3.11 random.Random (MT19937)","checkpoints":CHECKPOINTS})
def sample(out,b):
 q,seed=BRANCHES[b]; r=random.Random(seed); c=[0,0,0,0]; flips=onesx=onesy=0; raw=[]; cps=[]
 for i in range(1,N+1):
  x=r.getrandbits(1); f=int(r.random()<q); y=x^f; c[2*x+y]+=1; flips+=f; onesx+=x; onesy+=y
  if i<=2000: raw.append((i,x,f,y))
  if i in CHECKPOINTS: cps.append({"trials":i,"counts":c.copy(),"flips":flips})
 fields=("branch","q","seed","trials","n00","n01","n10","n11","flips","input_ones","output_ones")
 with (out/f"summary-{b}.csv").open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerow(dict(zip(fields,(b,format(q,'.17g'),seed,N,*c,flips,onesx,onesy))))
 with (out/f"raw-{b}.csv").open("w",newline="") as f: w=csv.writer(f);w.writerow(("trial","input","flip","output"));w.writerows(raw)
 dump(out/f"checkpoints-{b}.json",{"branch":b,"q":q,"seed":seed,"checkpoints":cps})
def summaries(out):
 a=[]
 for b in BRANCHES:
  with (out/f"summary-{b}.csv").open() as f:a.append(next(csv.DictReader(f)))
 return a
def aggregate(out):
 rows=[]
 for r in summaries(out):
  q=float(r["q"]); c=[int(r[x]) for x in ("n00","n01","n10","n11")]; qh=int(r["flips"])/N
  rows.append({"branch":r["branch"],"q":q,"q_hat":qh,"exact_capacity":1-h2(q),"plugin_capacity":1-h2(qh),"empirical_mutual_information":mi(c),"input_one_rate":int(r["input_ones"])/N,"output_one_rate":int(r["output_ones"])/N,"counts":c})
 dump(out/"aggregate.json",{"workflow_version":VERSION,"branches":rows})
 with (out/"aggregate.csv").open("w",newline="") as f:
  fields=[x for x in rows[0] if x!="counts"]+['n00','n01','n10','n11'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for x in rows:w.writerow({**{k:v for k,v in x.items() if k!="counts"},**dict(zip(fields[-4:],x["counts"]))})
def png(path,p):
 h=len(p);w=len(p[0])//3;raw=b"".join(b"\0"+bytes(r) for r in p)
 def ch(t,d):return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
 path.write_bytes(b"\x89PNG\r\n\x1a\n"+ch(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+ch(b"IDAT",zlib.compress(raw,9))+ch(b"IEND",b""))
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
 d=bytearray(b"GIF89a"+struct.pack("<HH",w,h)+b"\x81\x00\x00"+bytes((255,255,255,20,20,20,35,95,190,205,35,45)));d+=b"!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
 for fr in frames:
  codes=[]
  for v in fr:codes.extend((4,v))
  codes.append(5);packed=bytearray()
  for i in range(0,len(codes),2):packed.append(codes[i]|((codes[i+1] if i+1<len(codes) else 0)<<3))
  d+=b"!\xf9\x04\x00\x0c\x00\x00\x00,"+struct.pack("<HHHH",0,0,w,h)+b"\x00\x02"
  for i in range(0,len(packed),255):d+=bytes((len(packed[i:i+255]),))+packed[i:i+255]
  d+=b"\x00"
 d+=b";";path.write_bytes(d)
def render(out):
 a=json.loads((out/"aggregate.json").read_text())["branches"];p=[[255]*2400 for _ in range(650)];line(p,70,560,760,560,(20,20,20));line(p,70,60,70,560,(20,20,20))
 for key,col in (("exact_capacity",(20,20,20)),("plugin_capacity",(35,95,190)),("empirical_mutual_information",(205,35,45))):
  pts=[(70+round(x["q"]/.2*690),560-round(x[key]*500)) for x in a]
  for u,v in zip(pts,pts[1:]):line(p,*u,*v,col,2)
  for x,y in pts:line(p,x-4,y,x+4,y,col,3)
 for j,x in enumerate(a):
  c=x["counts"];m=max(c);ox=80+j*185
  for k,n in enumerate(c):
   xx=ox+(k%2)*70;yy=590-(k//2)*28;line(p,xx,yy,xx+55,yy,(35,95,190) if n/m>.5 else (205,35,45),5)
 png(out/"channel-capacity.png",p)
 cp={b:json.loads((out/f"checkpoints-{b}.json").read_text())["checkpoints"] for b in BRANCHES};frames=[]
 for upto in range(1,len(CHECKPOINTS)+1):
  fr=[0]*(640*360)
  def gl(x0,y0,x1,y1,c):
   dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
   while True:
    if 0<=x0<640 and 0<=y0<360:fr[y0*640+x0]=c
    if x0==x1 and y0==y1:break
    z=2*e
    if z>=dy:e+=dy;x0+=sx
    if z<=dx:e+=dx;y0+=sy
  gl(40,320,610,320,1);gl(40,20,40,320,1)
  for bi,(b,(q,_)) in enumerate(BRANCHES.items()):
   pts=[]
   for i,z in enumerate(cp[b][:upto]):pts.append((40+round(i*570/9),170-round(((z["flips"]/z["trials"])-q)*3000)))
   for u,v in zip(pts,pts[1:]):gl(*u,*v,2+(bi%2))
  frames.append(fr)
 gif(out/"convergence.gif",frames,640,360)
def validate(out,reference=None):
 checks=[]
 for b,r in zip(BRANCHES,summaries(out)):
  q,seed=BRANCHES[b];c=[int(r[x]) for x in ("n00","n01","n10","n11")];nx=(c[0]+c[1],c[2]+c[3]);raw=list(csv.DictReader((out/f"raw-{b}.csv").open()));qh=int(r["flips"])/N
  cond=(c[1]/nx[0],c[2]/nx[1]);ok=sum(c)==N and int(r["seed"])==seed and len(raw)==2000 and all(int(x["output"])==int(x["input"])^int(x["flip"]) for x in raw) and abs(qh-q)<=5*math.sqrt(q*(1-q)/N) and abs(int(r["input_ones"])/N-.5)<=5*math.sqrt(.25/N) and abs(int(r["output_ones"])/N-.5)<=5*math.sqrt(.25/N) and all(c) and all(abs(x-q)<=7*math.sqrt(q*(1-q)/n) for x,n in zip(cond,nx))
  checks.append({"branch":b,"pass":bool(ok)})
 a=json.loads((out/"aggregate.json").read_text())["branches"];orders=all(all(a[i][k]>a[i+1][k] for i in range(3)) for k in ("exact_capacity","plugin_capacity","empirical_mutual_information"));science=all(abs(x["empirical_mutual_information"]-x["exact_capacity"])<=.003 for x in a)
 files=["scenario.json","aggregate.json","aggregate.csv","channel-capacity.png","convergence.gif"]+[f"{x}-{b}.{e}" for b in BRANCHES for x,e in (("summary","csv"),("raw","csv"),("checkpoints","json"))];sums={f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in files};det=reference is None or all((out/f).read_bytes()==(Path(reference)/f).read_bytes() for f in files);overall=all(x["pass"] for x in checks) and orders and science and det
 dump(out/"validation.json",{"overall_pass":overall,"branches":checks,"monotonic_capacity_pass":orders,"mutual_information_pass":science,"deterministic_reference_pass":det,"checksums":sums,"limitations":["ideal memoryless channel numerical audit, not a physical experiment or coding theorem proof","MT19937 is not physical or cryptographic randomness","empirical mutual information has finite-sample bias"]})
 if not overall:raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument("mode",choices=("prepare","sample","aggregate","render","validate"));p.add_argument("--output",default=".");p.add_argument("--branch");p.add_argument("--reference");a=p.parse_args();o=Path(a.output);{"prepare":lambda:prepare(o),"sample":lambda:sample(o,a.branch),"aggregate":lambda:aggregate(o),"render":lambda:render(o),"validate":lambda:validate(o,a.reference)}[a.mode]()
if __name__=="__main__":main()
