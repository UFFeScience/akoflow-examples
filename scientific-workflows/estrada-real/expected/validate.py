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

df=pd.read_csv(out/'comparison.csv')
assert len(df)==104004 and (df.cost>0).all()
p=df.pivot(index=['profile','origin','destination'],columns='algorithm',values='cost')
assert len(p)==34668 and np.allclose(p.ucs,p.astar,atol=1e-6,rtol=0)
assert int((p.greedy-p.ucs>1e-6).sum())==3715

print(json.dumps({'status':'passed','validator':'independent artifact semantics, SHA-256 and scientific figure pixels','showcase':m['showcase'],'artifacts':len(m['artifacts'])}))
