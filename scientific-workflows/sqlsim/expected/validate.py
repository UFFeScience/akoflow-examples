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

with zipfile.ZipFile(out/'query-results.zip') as z:
    for name,dims in [('cube-2d',2),('cube-3d',3)]:
        df=pd.read_csv(io.BytesIO(z.read(name+'.csv')))
        columns=['spatial','metric'] if dims==2 else ['spatial','temporal','metric']
        assert int(df['count'].sum())==569*2**dims
        grand=df[df[columns].isna().all(axis=1)]
        assert len(grand)==1 and int(grand.iloc[0]['count'])==569
        a=pd.read_csv(io.BytesIO(z.read(name+'-assignments.csv')))
        assert len(a)==569 and a.id.nunique()==569 and a.metric.notna().all()

print(json.dumps({'status':'passed','validator':'independent artifact semantics, SHA-256 and scientific figure pixels','showcase':m['showcase'],'artifacts':len(m['artifacts'])}))
