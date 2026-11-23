#!/usr/bin/env python3
import argparse, hashlib, json, tempfile
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

MODELS = (("rdkit2d", "RDKit2D + MLP", 0.393, 0.024), ("cnn", "CNN", 0.446, 0.036), ("morgan", "Morgan + MLP", 0.908, 0.060))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--input",type=Path,required=True); parser.add_argument("--output",type=Path,required=True); parser.add_argument("--evidence",type=Path,required=True); args=parser.parse_args()
    source=json.loads(args.input.read_text()); args.output.parent.mkdir(parents=True,exist_ok=True); frames=[]
    with tempfile.TemporaryDirectory(prefix="caco2-models-") as tmp:
        for current in range(3):
            fig,ax=plt.subplots(figsize=(9.6,5.4),constrained_layout=True)
            labels=[m[1] for m in MODELS]; means=[source["results"][m[0]]["meanMae"] for m in MODELS]; stds=[source["results"][m[0]]["populationStd"] for m in MODELS]
            colors=["#111111" if i==current else "#b9b9b9" for i in range(3)]
            ax.errorbar(range(3),means,yerr=stds,fmt="none",ecolor=colors[current],capsize=7,zorder=1)
            ax.scatter(range(3),means,c=colors,s=150,zorder=2,label="Reproduced mean ± population SD (5 seeds)")
            published=[m[2] for m in MODELS]; ax.scatter(range(3),published,marker="x",c="#777777",s=100,label="Published mean")
            for i in range(current+1): ax.text(i,means[i]+stds[i]+0.035,f"{means[i]:.3f} ± {stds[i]:.3f}",ha="center")
            ax.set_xticks(range(3),labels); ax.set_ylim(.3,1.12); ax.set_ylabel("Fixed-test mean absolute error (lower is better)")
            ax.set_title(f"Model comparison {current+1}/3 · {labels[current]}"); ax.legend(frameon=False,loc="upper left")
            fig.suptitle("Caco2_Wang · five official scaffold splits · fixed 182-row test set")
            frame=Path(tmp)/f"frame-{current}.png"; fig.savefig(frame,dpi=100,metadata={"Software":"AkôFlow Community Explorer"}); plt.close(fig)
            with Image.open(frame) as image: frames.append(image.convert("P",palette=Image.Palette.ADAPTIVE))
        frames[0].save(args.output,save_all=True,append_images=frames[1:],duration=1200,loop=0,optimize=False,disposal=2)
    with Image.open(args.output) as image: count=image.n_frames; size=image.size; signature=args.output.read_bytes()[:6].decode()
    if count!=3 or signature not in {"GIF87a","GIF89a"}: raise RuntimeError("animation validation failed")
    evidence={"artifact":args.output.name,"artifact_sha256":digest(args.output),"source":str(args.input),"source_sha256":digest(args.input),"dimensions":list(size),"frames":count,"frame_duration_ms":1200,"evolving_dimension":"Sequential comparison of the three measured five-seed baseline results.","models":{m[0]:source["results"][m[0]] for m in MODELS}}
    args.evidence.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
