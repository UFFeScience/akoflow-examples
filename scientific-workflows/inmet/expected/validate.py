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

with zipfile.ZipFile(out/'observations.zip') as z:
    df=pd.read_csv(io.BytesIO(z.read('cleaned.csv')),parse_dates=['datetime'])
assert len(df)==87252 and df.datetime.nunique()==len(df)
assert df.datetime.min()==pd.Timestamp('2013-01-01')
assert df.datetime.max()==pd.Timestamp('2022-12-31 23:00:00')
assert set(df['WMO_Code'])=={'A701'}
assert df.Precip.notna().all() and (df.Precip>=0).all()
assert df.Temp.between(-20,60).all() and df.RH.between(0,100).all()

print(json.dumps({'status':'passed','validator':'independent artifact semantics, SHA-256 and scientific figure pixels','showcase':m['showcase'],'artifacts':len(m['artifacts'])}))
