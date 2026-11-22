#!/usr/bin/env python3
import argparse, csv, hashlib, itertools, json, math, random, struct, zlib
from pathlib import Path

VERSION = "community-chsh-singlet-v1"
N = 1_000_000
CHECKPOINTS = (100, 300, 1000, 3000, 10000, 30000, 100000, 300000, 1000000)
BRANCHES = {
    "a-b": (0.0, math.pi / 4, 1, 2026112201),
    "a-b-prime": (0.0, -math.pi / 4, 1, 2026112202),
    "a-prime-b": (math.pi / 2, math.pi / 4, 1, 2026112203),
    "a-prime-b-prime": (math.pi / 2, -math.pi / 4, -1, 2026112204),
}

def dump(path, obj):
    Path(path).write_text(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n")

def exact(x, y): return -math.cos(x - y)

def prepare(out):
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (x, y, sign, seed) in BRANCHES.items():
        rows.append({"branch": name, "alice_angle_radians": x, "bob_angle_radians": y,
                     "chsh_sign": sign, "seed": seed, "trials": N, "exact_correlation": exact(x, y)})
    dump(out / "scenario.json", {"workflow_version": VERSION, "paper_doi": "10.1103/PhysRevLett.23.880",
         "equation": "E(x,y)=-cos(x-y)", "aggregate": "abs(E_ab+E_abp+E_apb-E_apbp)",
         "prng": "Python 3.11 random.Random (MT19937)", "branches": rows})

def sample(out, branch):
    x, y, sign, seed = BRANCHES[branch]; target = exact(x, y); rng = random.Random(seed)
    product_sum = alice_sum = bob_sum = 0; checkpoints = []
    for i in range(1, N + 1):
        alice = 1 if rng.getrandbits(1) else -1
        product = 1 if rng.random() < (1 + target) / 2 else -1
        bob = alice * product
        product_sum += product; alice_sum += alice; bob_sum += bob
        if i in CHECKPOINTS:
            checkpoints.append({"trials": i, "product_sum": product_sum, "estimate": product_sum / i})
    fields = ["branch", "trials", "product_sum", "alice_sum", "bob_sum", "exact_correlation", "estimate", "standard_error", "seed", "alice_angle_radians", "bob_angle_radians", "chsh_sign"]
    row = {"branch": branch, "trials": N, "product_sum": product_sum, "alice_sum": alice_sum, "bob_sum": bob_sum,
           "exact_correlation": target, "estimate": product_sum / N,
           "standard_error": math.sqrt((1 - target * target) / N), "seed": seed,
           "alice_angle_radians": x, "bob_angle_radians": y, "chsh_sign": sign}
    with (out / f"correlation-{branch}.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerow(row)
    dump(out / f"checkpoints-{branch}.json", {"branch": branch, "checkpoints": checkpoints})

def enumerate_local(out):
    fields = ["A_a", "A_a_prime", "B_b", "B_b_prime", "chsh", "absolute_chsh"]
    rows = []
    for aa, ap, bb, bp in itertools.product((-1, 1), repeat=4):
        value = aa * bb + aa * bp + ap * bb - ap * bp
        rows.append(dict(zip(fields, (aa, ap, bb, bp, value, abs(value)))))
    with (out / "local-strategies.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def read_row(out, branch):
    with (out / f"correlation-{branch}.csv").open() as f: return next(csv.DictReader(f))

def aggregate(out):
    rows = [read_row(out, b) for b in BRANCHES]
    signed_sum = sum(int(r["chsh_sign"]) * int(r["product_sum"]) / int(r["trials"]) for r in rows)
    sample_s = abs(signed_sum); exact_s = 2 * math.sqrt(2)
    aggregate_se = math.sqrt(sum(float(r["standard_error"]) ** 2 for r in rows))
    checkpoints = []
    cps = {b: json.loads((out / f"checkpoints-{b}.json").read_text())["checkpoints"] for b in BRANCHES}
    for i, n in enumerate(CHECKPOINTS):
        s = abs(sum(BRANCHES[b][2] * cps[b][i]["product_sum"] / n for b in BRANCHES))
        checkpoints.append({"trials_per_branch": n, "sample_s": s})
    with (out / "aggregate.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["exact_s", "sample_s", "absolute_error", "aggregate_standard_error", "local_bound", "separation_standard_errors"]); w.writeheader()
        w.writerow({"exact_s": exact_s, "sample_s": sample_s, "absolute_error": abs(sample_s-exact_s), "aggregate_standard_error": aggregate_se, "local_bound": 2, "separation_standard_errors": (sample_s-2)/aggregate_se})
    dump(out / "metrics.json", {"workflow_version": VERSION, "exact_s": exact_s, "sample_s": sample_s,
         "absolute_error": abs(sample_s - exact_s), "aggregate_standard_error": aggregate_se,
         "five_se_tolerance": 5 * aggregate_se, "local_bound": 2,
         "separation_standard_errors": (sample_s - 2) / aggregate_se, "convergence": checkpoints})

def canvas(width, height, color=(255,255,255)):
    return [list(color) * width for _ in range(height)]

def line(pix, x0, y0, x1, y1, color, width=2):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        for oy in range(-width//2,width//2+1):
            for ox in range(-width//2,width//2+1):
                yy=y0+oy; xx=x0+ox
                if 0<=yy<len(pix) and 0<=xx<len(pix[0])//3: pix[yy][3*xx:3*xx+3]=color
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

FONT={"0":"111101101101111","1":"010110010010111","2":"111001111100111","3":"111001111001111","4":"101101111001001","5":"111100111001111","6":"111100111101111","7":"111001001001001","8":"111101111101111","9":"111101111001111",".":"000000000010010","-":"000000111000000","S":"111100111001111","=":"000111000111000"," ":"000000000000000"}
def text(pix,x,y,s,color=(0,0,0),scale=3):
    for ch in s:
        bits=FONT.get(ch,"000000000000000")
        for i,v in enumerate(bits):
            if v=="1":
                xx=x+(i%3)*scale; yy=y+(i//3)*scale
                for oy in range(scale):
                    for ox in range(scale):
                        if 0<=yy+oy<len(pix) and 0<=xx+ox<len(pix[0])//3: pix[yy+oy][3*(xx+ox):3*(xx+ox)+3]=color
        x += 4*scale

def png(path,pix):
    h=len(pix); w=len(pix[0])//3; raw=b"".join(b"\0"+bytes(row) for row in pix)
    def chunk(kind,data): return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))

def gif_lzw(indices,min_code_size=2):
    clear=1<<min_code_size; end=clear+1; code_size=min_code_size+1; table={bytes([i]):i for i in range(clear)}; next_code=end+1; codes=[clear]; w=b""
    for k in indices:
        wk=w+bytes([k])
        if wk in table: w=wk; continue
        codes.append(table[w]); table[wk]=next_code; next_code+=1; w=bytes([k])
        if next_code==(1<<code_size) and code_size<12: code_size+=1
        if next_code>=4095: codes.append(clear); table={bytes([i]):i for i in range(clear)}; next_code=end+1; code_size=min_code_size+1
    if w: codes.append(table[w])
    codes.append(end)
    out=bytearray(); cur=0; bits=0; code_size=min_code_size+1; next_code=end+1; old=False
    for code in codes:
        cur|=code<<bits; bits+=code_size
        while bits>=8: out.append(cur&255); cur>>=8; bits-=8
        if code==clear: code_size=min_code_size+1; next_code=end+1; old=False
        elif code!=end:
            if old: next_code+=1
            old=True
            if next_code==(1<<code_size) and code_size<12: code_size+=1
    if bits: out.append(cur&255)
    return bytes(out)

def gif(path,frames,w,h):
    data=bytearray(b"GIF89a"+struct.pack("<HH",w,h)+b"\x81\x00\x00"+bytes((255,255,255,0,0,0,40,100,210,210,40,40)))
    data+=b"!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
    for indices in frames:
        data+=b"!\xf9\x04\x00\x0c\x00\x00\x00"+b","+struct.pack("<HHHH",0,0,w,h)+b"\x00\x02"
        compressed=gif_lzw(indices)
        for i in range(0,len(compressed),255): data+=bytes([len(compressed[i:i+255])])+compressed[i:i+255]
        data+=b"\x00"
    data+=b";"; Path(path).write_bytes(data)

def render(out):
    rows=[read_row(out,b) for b in BRANCHES]; metrics=json.loads((out/"metrics.json").read_text())
    pix=canvas(900,520); line(pix,70,450,850,450,(0,0,0)); line(pix,70,50,70,450,(0,0,0))
    for i,r in enumerate(rows):
        ex=float(r["exact_correlation"]); est=float(r["estimate"]); x=150+i*190
        y1=int(250-ex*180); y2=int(250-est*180); line(pix,x-20,250,x-20,y1,(0,0,0),18); line(pix,x+20,250,x+20,y2,(40,100,210),18)
        text(pix,x-36,470,str(i+1),scale=3)
    text(pix,75,15,"S="+f'{metrics["sample_s"]:.6f}',scale=4); png(out/"correlations.png",pix)
    pix=canvas(900,520); line(pix,100,450,820,450,(0,0,0)); scale=120
    line(pix,150,450,150,450-int(2*scale),(210,40,40),55); line(pix,420,450,420,450-int(metrics["exact_s"]*scale),(0,0,0),55); line(pix,690,450,690,450-int(metrics["sample_s"]*scale),(40,100,210),55)
    text(pix,105,465,"2.000",scale=3); text(pix,365,465,f'{metrics["exact_s"]:.3f}',scale=3); text(pix,635,465,f'{metrics["sample_s"]:.3f}',scale=3); png(out/"chsh-bound.png",pix)
    frames=[]; conv=metrics["convergence"]
    for end in range(1,len(conv)+1):
        idx=[0]*(640*360)
        def gl(x0,y0,x1,y1,c):
            dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; e=dx+dy
            while True:
                if 0<=x0<640 and 0<=y0<360: idx[y0*640+x0]=c
                if x0==x1 and y0==y1: break
                e2=2*e
                if e2>=dy:e+=dy;x0+=sx
                if e2<=dx:e+=dx;y0+=sy
        gl(50,300,610,300,1); gl(50,40,50,300,1); gl(50,int(300-(2-1.8)/1.2*240),610,int(300-(2-1.8)/1.2*240),3)
        pts=[]
        for i,p in enumerate(conv[:end]): pts.append((50+i*560/(len(conv)-1),int(300-(p["sample_s"]-1.8)/1.2*240)))
        for a,b in zip(pts,pts[1:]): gl(round(a[0]),a[1],round(b[0]),b[1],2)
        frames.append(idx)
    gif(out/"convergence.gif",frames,640,360)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate(out, reference=None):
    rows=[read_row(out,b) for b in BRANCHES]; metrics=json.loads((out/"metrics.json").read_text())
    with (out/"local-strategies.csv").open() as f: local=list(csv.DictReader(f))
    branch_results=[]
    for b,r in zip(BRANCHES,rows):
        target=exact(BRANCHES[b][0],BRANCHES[b][1]); n=int(r["trials"]); estimate=int(r["product_sum"])/n; se=float(r["standard_error"])
        branch_results.append({"branch":b,"absolute_error":abs(estimate-target),"five_se":5*se,"pass":n==N and int(r["seed"])==BRANCHES[b][3] and abs(float(r["exact_correlation"])-target)<=1e-15 and abs(estimate-target)<=5*se and abs(int(r["alice_sum"]))<N and abs(int(r["bob_sum"]))<N})
    files=["scenario.json"]+[f"correlation-{b}.csv" for b in BRANCHES]+[f"checkpoints-{b}.json" for b in BRANCHES]+["local-strategies.csv","aggregate.csv","metrics.json","correlations.png","chsh-bound.png","convergence.gif"]
    checksums={f:sha(out/f) for f in files}; deterministic=True
    if reference:
        deterministic=all((out/f).read_bytes()==(Path(reference)/f).read_bytes() for f in files)
    local_ok=len(local)==16 and len({tuple(r[k] for k in ("A_a","A_a_prime","B_b","B_b_prime")) for r in local})==16 and max(int(r["absolute_chsh"]) for r in local)==2
    overall=all(r["pass"] for r in branch_results) and abs(metrics["exact_s"]-2*math.sqrt(2))<=1e-12 and metrics["absolute_error"]<=metrics["five_se_tolerance"] and metrics["separation_standard_errors"]>=100 and local_ok and deterministic
    dump(out/"validation.json",{"workflow_version":VERSION,"overall_pass":overall,"branches":branch_results,"exact_aggregate_pass":abs(metrics["exact_s"]-2*math.sqrt(2))<=1e-12,"sample_aggregate_pass":metrics["absolute_error"]<=metrics["five_se_tolerance"],"bound_separation_pass":metrics["separation_standard_errors"]>=100,"local_enumeration_pass":local_ok,"deterministic_reference_pass":deterministic,"checksums":checksums,"limitations":["ideal singlet law is sampled directly","not a laboratory Bell test","does not address experimental loopholes","MT19937 is deterministic and not cryptographic"]})
    if not overall: raise SystemExit(1)

def main():
    p=argparse.ArgumentParser(); p.add_argument("mode",choices=("prepare","sample","enumerate","aggregate","render","validate")); p.add_argument("--output",default="."); p.add_argument("--branch"); p.add_argument("--reference"); a=p.parse_args(); out=Path(a.output)
    {"prepare":lambda:prepare(out),"sample":lambda:sample(out,a.branch),"enumerate":lambda:enumerate_local(out),"aggregate":lambda:aggregate(out),"render":lambda:render(out),"validate":lambda:validate(out,a.reference)}[a.mode]()
if __name__=="__main__": main()
