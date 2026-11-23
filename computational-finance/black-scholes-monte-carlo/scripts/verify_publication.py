#!/usr/bin/env python3
import json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE="https://hub.akoflow.com/o/akoflow/community-explorer-issue-52-black-scholes-monte-carlo-v1"
PUBLICATION="e5285dc8-6a79-4f61-8540-6f68206f2c05"
RUN=f"{BASE}/results/1/executions/06b6116e-397c-4af7-b434-1338a4f87857/runs/community-black-scholes-run-v1/workflow"
YAML=f"https://hub.akoflow.com/api/v1/publications/{PUBLICATION}/versions/1/yaml"
RESULTS=f"{BASE}/versions/1/results.json"
RAW="https://raw.githubusercontent.com/UFFeScience/akoflow-examples/817c37a/computational-finance/black-scholes-monte-carlo/"
def get(url):
    request=urllib.request.Request(url,headers={"User-Agent":"akoflow-community-public-verifier/1"})
    with urllib.request.urlopen(request,timeout=60) as response:return response.status,response.headers.get_content_type(),response.read()
page_status,_,page=get(BASE);run_status,_,run=get(RUN);yaml_status,yaml_type,yaml=get(YAML);results_status,results_type,results=get(RESULTS)
assets={}
for name,path,signature in (("price_figure","outputs/reference/price-convergence.png",b"\x89PNG\r\n\x1a\n"),("scaling_figure","outputs/reference/standard-error-scaling.png",b"\x89PNG\r\n\x1a\n"),("animation","outputs/reference/option-convergence.gif",b"GIF89a"),("timeline","evidence/measured-timeline.svg",b"<svg")):
    status,media,data=get(RAW+path);assets[name]={"http_status":status,"bytes":len(data),"media_type":media,"signature_ok":data.lstrip().startswith(signature)}
    if name=="animation":assets[name]["frames"]=data.count(b"\x21\xf9\x04")
text=page.decode();run_text=run.decode();yaml_text=yaml.decode()
report={"anonymous":True,"verified_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"project_id":"44e9e6b5-454b-43b9-bf73-240be5e31aab","publication_id":PUBLICATION,"version":1,"page":{"http_status":page_status,"bytes":len(page),"embedded_readme_images":text.count('class="readme-image"'),"authorship_identified":'authorship\\\":\\\"identified' in text,"citation_present":"10.1086/260062" in text},"recorded_run":{"http_status":run_status,"completed":"community-black-scholes-run-v1" in run_text and "completed" in run_text,"result_files":all(name in run_text for name in ("price-convergence.png","standard-error-scaling.png","option-convergence.gif"))},"import_yaml":{"http_status":yaml_status,"bytes":len(yaml),"media_type":yaml_type,"workflow_name":"community-black-scholes-monte-carlo-v1" in yaml_text,"portable_build_count":yaml_text.count("type: build"),"context_archive_count":yaml_text.count("contextArchive:"),"context_digest_present":"b78ece52089c87d6027d8b11222438b5e78ef80f8a054e539e84eae4e2a0bdb8" in yaml_text,"recipe_digest_present":"3b7670abfba77615adecada50b936ec53be36988ba48dcde7c52acd438b88dbb" in yaml_text},"experiment_download":{"http_status":results_status,"bytes":len(results),"media_type":results_type},"gallery":assets,"result_consistency":json.loads((ROOT/"evidence"/"daemon-result-agreement.json").read_text())}
checks=[page_status==200,run_status==200,yaml_status==200,results_status==200,report["page"]["embedded_readme_images"]==4,report["page"]["authorship_identified"],report["page"]["citation_present"],report["recorded_run"]["completed"],report["recorded_run"]["result_files"],report["import_yaml"]["portable_build_count"]==8,report["import_yaml"]["context_archive_count"]==8,report["import_yaml"]["context_digest_present"],report["import_yaml"]["recipe_digest_present"],assets["animation"]["frames"]>1,all(x["http_status"]==200 and x["signature_ok"] for x in assets.values()),report["result_consistency"]["passed"]]
report["passed"]=all(checks)
(ROOT/"evidence"/"public-verification.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
if not report["passed"]:raise SystemExit("anonymous public verification failed")
