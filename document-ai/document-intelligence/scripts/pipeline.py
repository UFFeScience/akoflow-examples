#!/usr/bin/env python3
import argparse, csv, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def dump(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2)+"\n")
def ingest(out):
 docs=[]
 for p in sorted((ROOT/'data/documents').glob('*.txt')):
  text=p.read_text(); docs.append({'file':p.name,'sha256':hashlib.sha256(text.encode()).hexdigest(),'text':text})
 dump(out/'ingested.json',docs)
def classify(out):
 docs=json.loads((out/'ingested.json').read_text())
 dump(out/'classified.json',[{**d,'type':next(x.split(':',1)[1].strip().lower() for x in d['text'].splitlines() if x.startswith('DOCUMENT:'))} for d in docs])
def extract(out):
 result=[]
 for d in json.loads((out/'classified.json').read_text()):
  fields={}; items=[]
  for line in d['text'].splitlines():
   if ': ' not in line: continue
   key,val=line.split(': ',1)
   if key=='ITEM':
    name,qty,price=[x.strip() for x in val.split('|')]; items.append({'name':name,'quantity':int(qty),'unit_price':float(price)})
   else: fields[key.lower()]=val
  result.append({'file':d['file'],'sha256':d['sha256'],'type':d['type'],'fields':fields,'items':items})
 dump(out/'extracted.json',result)
def reconcile(out):
 docs=json.loads((out/'extracted.json').read_text()); rows=[]; seen=set()
 for d in docs:
  if d['type']!='invoice': continue
  f=d['fields']; subtotal=sum(i['quantity']*i['unit_price'] for i in d['items']); total=float(f['total']); tax=float(f['tax']); iid=f['invoice_id']
  rows.append({'invoice_id':iid,'supplier':f['supplier'],'subtotal':subtotal,'tax':tax,'total':total,'balanced':abs(subtotal+tax-total)<.01,'duplicate':iid in seen}); seen.add(iid)
 dump(out/'reconciliation.json',rows)
 with (out/'invoice-summary.csv').open('w',newline='') as fp:
  w=csv.DictWriter(fp,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def report(out):
 rows=json.loads((out/'reconciliation.json').read_text()); ok=all(r['balanced'] and not r['duplicate'] for r in rows)
 dump(out/'report.json',{'status':'passed' if ok else 'failed','documents':len(json.loads((out/'ingested.json').read_text())),'invoices':len(rows),'gross_total':sum(r['total'] for r in rows)})
 artifacts=['ingested.json','classified.json','extracted.json','reconciliation.json','invoice-summary.csv','report.json']
 dump(out/'manifest.json',{'showcase':'document-intelligence','status':'success' if ok else 'failed','artifacts':artifacts})
STAGES={'ingest':ingest,'classify':classify,'extract':extract,'reconcile':reconcile,'report':report}
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=[*STAGES,'all'],default='all');p.add_argument('--output',required=True);a=p.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=True)
 for s in list(STAGES) if a.stage=='all' else [a.stage]: STAGES[s](o)
if __name__=='__main__':main()

