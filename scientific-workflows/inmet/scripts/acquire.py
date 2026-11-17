import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile
from remotezip import RemoteZip

root=Path(__file__).resolve().parents[1];data=root/'data';dest=data/'inputs';dest.mkdir(exist_ok=True)
cfg=json.loads((data/'sources.json').read_text());members=json.loads((data/'members.json').read_text())
old={}
if (data/'acquisition.json').exists():old={v['path']:v for v in json.loads((data/'acquisition.json').read_text())['files']}
receipts=[]
def save(path,b,url,extra=None):
    h=hashlib.sha256(b).hexdigest()
    if path in old and old[path]['sha256']!=h:raise RuntimeError('Frozen source changed: '+path)
    p=dest/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    receipts.append(dict(path=path,url=url,sha256=h,bytes=len(b),**(extra or {})))
notebook=dest/'original.ipynb'
if notebook.exists():b=notebook.read_bytes()
else:b=urllib.request.urlopen(cfg['notebook'],timeout=60).read()
assert hashlib.md5(b).hexdigest()=='5af1378b16fae429866cc4a204cc5b50'
save('original.ipynb',b,cfg['notebook'])
missing=[n for n in members['names'] if not (dest/'raw'/n).exists()]
if missing:
    with zipfile.ZipFile(RemoteZip(cfg['archive'],members['length'],members['offset'])) as archive:
        for name in members['names']:
            p=dest/'raw'/name
            b=p.read_bytes() if p.exists() else archive.read(name)
            save('raw/'+name,b,cfg['archive'],{'archiveMember':'dataset/dataset.zip!/'+name})
            print('Verified',name,len(b),flush=True)
else:
    for name in members['names']:save('raw/'+name,(dest/'raw'/name).read_bytes(),cfg['archive'],{'archiveMember':'dataset/dataset.zip!/'+name})
(data/'acquisition.json').write_text(json.dumps({'files':receipts},indent=2)+'\n')
