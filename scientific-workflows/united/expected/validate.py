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
assert len(df)==8 and set(df.detector)=={'arima','rolling'}
assert (df[['tn','fp','fn','tp']].sum(axis=1)==df.test_points).all()
precision=np.divide(df.tp,df.tp+df.fp,out=np.zeros(len(df)),where=(df.tp+df.fp).to_numpy()!=0)
recall=np.divide(df.tp,df.tp+df.fn,out=np.zeros(len(df)),where=(df.tp+df.fn).to_numpy()!=0)
f1=np.divide(2*precision*recall,precision+recall,out=np.zeros(len(df)),where=precision+recall!=0)
assert np.allclose(df.f1,f1)
assert df.groupby('series').points.first().sum()==16128

print(json.dumps({'status':'passed','validator':'independent artifact semantics, SHA-256 and scientific figure pixels','showcase':m['showcase'],'artifacts':len(m['artifacts'])}))
