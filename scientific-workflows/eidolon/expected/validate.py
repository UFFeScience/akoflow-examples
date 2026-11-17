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

with zipfile.ZipFile(out/'computed-collections.zip') as z:
    for name,series,points in [('climate',10,630),('bioenergy',20,660),('emissions',20,1220)]:
        df=pd.read_csv(io.BytesIO(z.read(name+'.csv')))
        assert df.series.nunique()==series and len(df)==points
        assert df.groupby('series').year.nunique().min()>20
        assert df.value.notna().any()
assert all(r['referenceAgreement'] for r in v['findings']['collections'])

print(json.dumps({'status':'passed','validator':'independent artifact semantics, SHA-256 and scientific figure pixels','showcase':m['showcase'],'artifacts':len(m['artifacts'])}))
