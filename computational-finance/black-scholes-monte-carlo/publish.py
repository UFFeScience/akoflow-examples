#!/usr/bin/env python3
import json, os, urllib.error, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent; EVIDENCE=ROOT/"evidence"
API=os.environ.get("AKOFLOW_API_URL","http://127.0.0.1:8080/akoflow-api").rstrip("/")
TOKEN=os.environ.get("AKOFLOW_API_TOKEN","akoflow-development-token")
PROJECT="44e9e6b5-454b-43b9-bf73-240be5e31aab"
KEY="community-explorer-issue-52-black-scholes-monte-carlo-v1"
RUN="community-black-scholes-run-v1"
def call(path,value=None):
    request=urllib.request.Request(f"{API}/{path.lstrip('/')}",data=None if value is None else json.dumps(value).encode(),headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"},method="GET" if value is None else "POST")
    try:
        with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)
    except urllib.error.HTTPError as error:raise SystemExit(f"Hub API {error.code} {path}: {error.read().decode()}") from None
status=call("hub/status/")
if not status.get("connected"):raise SystemExit("Hub is not connected; publication only is blocked")
if status["identity"]["projectId"]!=PROJECT:raise SystemExit("Connected Hub destination is not the Community Explorer production project")
receipt_path=EVIDENCE/"hub-publication.json"
if receipt_path.exists():
    receipt=json.loads(receipt_path.read_text())
    if receipt.get("persistentPublicationKey")==KEY and receipt.get("runId")==RUN and receipt.get("projectId")==PROJECT:print(json.dumps(receipt,indent=2));raise SystemExit(0)
publications=call("hub/publications/")
publication=next((item for item in publications if item["slug"]==KEY),None)
if publication is None:
    publication=call("hub/publications/",{"title":"Black–Scholes risk-neutral Monte Carlo convergence audit","slug":KEY,"description":"Validated paired call/put Monte Carlo convergence, put–call parity, and inverse-square-root uncertainty scaling. Persistent key: community-explorer-issue-52-black-scholes-monte-carlo-v1.","readme":(ROOT/"README.md").read_text(),"visibility":"public","authorship":"Fischer Black and Myron Scholes (analytic scientific source); UFFeScience contributors (Monte Carlo adaptation, implementation, and validation)"})
preview=call("hub/publications/preview/",{"runId":RUN,"publicationId":publication["id"],"message":"Issue #52 validated reference run: 8/8 activities completed; fixed price, parity, moment, uncertainty-scaling, deterministic-media, and measured-overlap gates passed.","content":{"files":True,"events":True,"metrics":True,"logs":False,"machineLabel":"Community Explorer CPU"}})
(EVIDENCE/"hub-preview.json").write_text(json.dumps(preview,indent=2,sort_keys=True)+"\n")
review=preview["review"]
if review["experiment"]["executionCount"]!=1 or review["experiment"]["activityCount"]!=8:raise SystemExit("Hub preview does not match the recorded run")
if any(row["summary"]["status"]!="completed" for row in review["results"]):raise SystemExit("Hub preview includes an incomplete result")
receipt=call("hub/publications/confirm/",{"previewId":preview["id"],"acknowledgePublic":True})
receipt.update({"publicationId":publication["id"],"projectId":PROJECT,"persistentPublicationKey":KEY,"runId":RUN,"hubOrigin":status["hubUrl"],"url":f"{status['hubUrl'].rstrip('/')}/o/akoflow/{KEY}","uri":f"akoflow://hub/publications/{publication['id']}/versions/{receipt['version']}"})
receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,indent=2))
