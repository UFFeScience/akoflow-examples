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

rows=json.loads((out/'query-results.json').read_text())
assert len(rows)==8
aligned=[r for r in rows if r['mode']=='aligned']
ref=pd.DataFrame(aligned[0]['groups']).sort_values(['returnflag','linestatus']).reset_index(drop=True)
numeric=[c for c in ref if c not in ['returnflag','linestatus']]
for r in aligned[1:]:
    table=pd.DataFrame(r['groups']).sort_values(['returnflag','linestatus']).reset_index(drop=True)
    assert table[['returnflag','linestatus']].equals(ref[['returnflag','linestatus']])
    assert np.allclose(table[numeric],ref[numeric],rtol=1e-9,atol=1e-6)
original={r['engine']:r['matchedRows'] for r in rows if r['mode']=='original' and not r['indexed']}
assert original['mongo']>original['postgres']

print(json.dumps({'status':'passed','validator':'independent artifact semantics, SHA-256 and scientific figure pixels','showcase':m['showcase'],'artifacts':len(m['artifacts'])}))
