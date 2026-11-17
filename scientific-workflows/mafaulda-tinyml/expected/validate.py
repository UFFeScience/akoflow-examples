import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
from PIL import Image

out=Path('/outputs')
m=json.loads((out/'manifest.json').read_text())
v=json.loads((out/'scientific-validation.json').read_text())
assert m['status']=='success' and v['status']=='passed'
for name in m['artifacts']:
    p=out/name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'][name],name
    if p.suffix=='.png':
        with Image.open(p) as image:
            assert min(image.size)>100 and np.asarray(image).std()>1

df=pd.read_csv(out/'metrics.csv')
assert len(df)==9 and df.f1.between(0,1).all() and (df.sizeKiB>0).all()
assert (df.calibrationTestOverlap==0).all()
with zipfile.ZipFile(out/'quantized-models.zip') as z:
    assert len(z.namelist())==9
    for name in z.namelist():
        b=z.read(name);assert b[4:8]==b'TFL3'
        r=df[(df.model==name.split('-')[0])&(df.quantization==name.split('-')[1].split('.')[0])].iloc[0]
        assert len(b)/1024==r.sizeKiB
for r in v['findings']['baselineModels']:
    assert len(r['folds'])==5 and all(f['testRecordings']==6 for f in r['folds'])
    assert np.asarray(r['lastFoldConfusion']).sum()==300

print(json.dumps({'status':'passed','validator':'independent artifact semantics, SHA-256 and scientific figure pixels','showcase':m['showcase'],'artifacts':len(m['artifacts'])}))
