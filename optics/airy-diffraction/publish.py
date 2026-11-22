#!/usr/bin/env python3
import json,os,urllib.error,urllib.request
from pathlib import Path

root=Path(__file__).resolve().parent;evidence=root/'evidence';config=json.loads((root/'data/input.json').read_text())
api=os.environ.get('AKOFLOW_API_URL','http://127.0.0.1:8080/akoflow-api').rstrip('/');token=os.environ.get('AKOFLOW_API_TOKEN','akoflow-development-token')
def call(path,value=None):
 req=urllib.request.Request(f"{api}/{path.lstrip('/')}",data=None if value is None else json.dumps(value).encode(),headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'},method='GET' if value is None else 'POST')
 try:
  with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)
 except urllib.error.HTTPError as error:raise SystemExit(f"Hub API {error.code} {path}: {error.read().decode()}") from None
status=call('hub/status/')
if not status.get('connected'):raise SystemExit('Hub is not connected; publication only is blocked')
if status['identity']['projectId']!=config['projectId']:raise SystemExit('Connected Hub destination is not the Community Explorer production project')
key=config['persistentPublicationKey'];run_id='community-airy-diffraction-run-v1';receipt_path=evidence/'hub-publication.json'
if receipt_path.exists():
 receipt=json.loads(receipt_path.read_text())
 if receipt.get('persistentPublicationKey')==key and receipt.get('runId')==run_id and receipt.get('projectId')==config['projectId']:
  print(json.dumps(receipt,indent=2));raise SystemExit(0)
publications=call('hub/publications/');publication=next((item for item in publications if item['slug']==key),None)
readme=(root/'README.md').read_text();base='https://raw.githubusercontent.com/UFFeScience/akoflow-examples/54fc918268cc403c69981c0facc37f64dd9f5286/optics/airy-diffraction/'
readme=readme.replace('](outputs/',']('+base+'outputs/').replace('](evidence/',']('+base+'evidence/')
if publication is None:
 publication=call('hub/publications/',{'title':config['title'],'slug':key,'description':'Validated scalar circular-aperture diffraction audit with Bessel roots, encircled energy, wavelength scaling, and measured parallel execution.','readme':readme,'visibility':'public','authorship':'George Biddell Airy (scientific source); UFFeScience contributors (implementation)'})
preview=call('hub/publications/preview/',{'runId':run_id,'publicationId':publication['id'],'message':'Issue #37 validated reference run: 7/7 activities completed; all fixed scientific, determinism, media, and parallel-overlap gates passed.','content':{'files':True,'events':True,'metrics':True,'logs':False,'machineLabel':'Community Explorer CPU'}})
(evidence/'hub-preview.json').write_text(json.dumps(preview,indent=2,sort_keys=True)+'\n');review=preview['review']
if review['experiment']['executionCount']!=1 or review['experiment']['activityCount']!=7:raise SystemExit('Hub preview does not match the recorded run')
if any(row['summary']['status']!='completed' for row in review['results']):raise SystemExit('Hub preview includes an incomplete result')
receipt=call('hub/publications/confirm/',{'previewId':preview['id'],'acknowledgePublic':True})
receipt.update({'publicationId':publication['id'],'projectId':config['projectId'],'persistentPublicationKey':key,'runId':run_id,'hubOrigin':status['hubUrl'],'url':f"{status['hubUrl'].rstrip('/')}/o/akoflow/{key}",'uri':f"akoflow://hub/publications/{publication['id']}/versions/{receipt['version']}"})
receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt,indent=2))
