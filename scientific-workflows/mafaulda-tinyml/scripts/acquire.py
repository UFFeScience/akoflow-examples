import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile
from remotezip import RemoteZip

root=Path(__file__).resolve().parents[1];data=root/'data';dest=data/'inputs';dest.mkdir(exist_ok=True)
cfg=json.loads((data/'sources.json').read_text());old={}
if (data/'acquisition.json').exists():old={v['path']:v for v in json.loads((data/'acquisition.json').read_text())['files']}
def save(path,b,url,extra=None):
    h=hashlib.sha256(b).hexdigest()
    if path in old and old[path]['sha256']!=h:raise RuntimeError('Frozen source changed: '+path)
    p=dest/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    return dict(path=path,url=url,sha256=h,bytes=len(b),**(extra or {}))
p=dest/'original.ipynb'
b=p.read_bytes() if p.exists() else urllib.request.urlopen(cfg['notebook'],timeout=60).read()
receipts=[save('original.ipynb',b,cfg['notebook'])]
def acquire_class(name):
    url=cfg['datasetBase']+name+'.zip'
    existing=[v for v in old.values() if v.get('class')==name]
    if len(existing)==cfg['recordingsPerClass'] and all((dest/v['path']).exists() for v in existing):
        return [save(v['path'],(dest/v['path']).read_bytes(),url,{'class':name,'archiveMember':v['archiveMember']}) for v in existing]
    with zipfile.ZipFile(RemoteZip(url)) as archive:
        names=sorted(n for n in archive.namelist() if n.endswith('.csv'))
        count=cfg['recordingsPerClass']
        selected=[v['archiveMember'] for v in existing] if len(existing)==count else [names[round(i*(len(names)-1)/(count-1))] for i in range(count)]
        result=[]
        for n in selected:
            path='recordings/'+n
            b=(dest/path).read_bytes() if (dest/path).exists() else archive.read(n)
            result.append(save(path,b,url,{'class':name,'archiveMember':n}))
            print('Verified',n,len(b),flush=True)
        return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for records in pool.map(acquire_class,cfg['classes']):receipts.extend(records)
(data/'acquisition.json').write_text(json.dumps({'files':sorted(receipts,key=lambda r:r['path'])},indent=2)+'\n')
