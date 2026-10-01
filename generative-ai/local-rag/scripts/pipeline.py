#!/usr/bin/env python3
import argparse, hashlib, json, math, re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def tok(s): return re.findall(r"[a-z0-9]+",s.lower())
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+"\n")
def ingest(o):
 docs=[{'id':p.stem,'text':p.read_text(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((ROOT/'data/corpus').glob('*.md'))]
 dump(o/'documents.json',docs)
def chunk(o):
 chunks=[]
 for d in json.loads((o/'documents.json').read_text()):
  sentences=[x.strip() for x in re.split(r'(?<=[.!?])\s+',d['text'].replace('\n',' ')) if x.strip()]
  for i in range(0,len(sentences),2):chunks.append({'id':f"{d['id']}:{i//2}",'source':d['id'],'text':' '.join(sentences[i:i+2])})
 dump(o/'chunks.json',chunks)
def index(o):
 chunks=json.loads((o/'chunks.json').read_text()); n=len(chunks); df=Counter()
 for c in chunks:df.update(set(tok(c['text'])))
 vectors=[]
 for c in chunks:
  tf=Counter(tok(c['text']));v={w:(1+math.log(cn))*math.log((n+1)/(df[w]+1))+1 for w,cn in tf.items()};norm=math.sqrt(sum(x*x for x in v.values())) or 1
  vectors.append({'id':c['id'],'source':c['source'],'text':c['text'],'vector':{w:x/norm for w,x in v.items()}})
 dump(o/'index.json',vectors)
def retrieve(o):
 idx=json.loads((o/'index.json').read_text());qs=json.loads((ROOT/'data/questions.json').read_text());results=[]
 for q in qs:
  words=Counter(tok(q['question']));norm=math.sqrt(sum(x*x for x in words.values())) or 1
  ranked=sorted(((sum(v['vector'].get(w,0)*c/norm for w,c in words.items()),v) for v in idx),key=lambda item:item[0],reverse=True)
  hit=ranked[0][1];results.append({**q,'chunk_id':hit['id'],'source':hit['source'],'score':round(ranked[0][0],6),'evidence':hit['text']})
 dump(o/'retrieval.json',results)
def answer(o):
 rs=json.loads((o/'retrieval.json').read_text());answers=[]
 for r in rs:
  sentences=re.split(r'(?<=[.!?])\s+',r['evidence']);best=max(sentences,key=lambda s:len(set(tok(s))&set(tok(r['question']))))
  answers.append({'question':r['question'],'answer':best,'citation':r['source'],'grounded':r['expected'].lower() in r['evidence'].lower()})
 dump(o/'answers.json',answers)
def evaluate(o):
 a=json.loads((o/'answers.json').read_text());score=sum(x['grounded'] for x in a)/len(a);dump(o/'evaluation.json',{'questions':len(a),'grounded_accuracy':score})
 arts=['documents.json','chunks.json','index.json','retrieval.json','answers.json','evaluation.json'];dump(o/'manifest.json',{'showcase':'local-rag-factory','status':'success' if score==1 else 'failed','artifacts':arts})
S={'ingest':ingest,'chunk':chunk,'index':index,'retrieve':retrieve,'answer':answer,'evaluate':evaluate}
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=[*S,'all'],default='all');p.add_argument('--output',required=True);a=p.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=True)
 for s in list(S) if a.stage=='all' else [a.stage]:S[s](o)
if __name__=='__main__':main()
