import argparse,hashlib,json,tarfile,tempfile,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--definition',action='store_true');p.add_argument('--output',default='/outputs');args=p.parse_args()
app=Path('/app');w=json.loads((app/'workflow.json').read_text());m=json.loads((app/'data/input-verification.json').read_text())
assert len(w['spec']['activities'])==4 and len(m['files'])==4
assert m['reads']==1039872 and m['bases']==53033472 and sum(f['bytes'] for f in m['files'])==52550954
assert hashlib.sha256((app/'upstream/rnaseq/nextflow.config').read_bytes()).hexdigest()==json.loads((app/'data/upstream.json').read_text())['nextflowConfigSHA256']
assert len(list(Path('/opt/nf-env-locks').glob('*.txt')))==16
if args.definition:
 print(json.dumps({'status':'success','definitionOnly':True,'outerActivities':4,'originalPipeline':'nf-core/rnaseq 3.27.0','fullLibraryReads':1039872,'dependencyEnvironments':16}));raise SystemExit
out=Path(args.output);s=json.loads((out/'rnaseq-summary.json').read_text());assert s['status']=='success' and not s['differentialExpressionClaimed'] and not s['run']['subsampledForQuantification']
with tempfile.TemporaryDirectory() as temporary:
 t=Path(temporary)
 with tarfile.open(out/'rnaseq-results.tar.gz') as a:
  assert len(a.getnames())==len(set(a.getnames()))
  assert set(a.getnames())==set(s['resultSHA256'])|{'rnaseq-summary.json'}
  for f in a.getmembers():
   assert f.isfile() and not Path(f.name).is_absolute() and '..' not in Path(f.name).parts
   dest=t/f.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(a.extractfile(f).read())
 assert json.loads((t/'rnaseq-summary.json').read_text())==s
 for name,sha in s['resultSHA256'].items():assert hashlib.sha256((t/name).read_bytes()).hexdigest()==sha
 trace=pd.read_csv(t/'nextflow-trace.tsv',sep='\t');assert len(trace)==s['run']['innerCompletedTasks']>5 and (trace.status=='COMPLETED').all() and (trace.exit.astype(str)=='0').all()
 tasks=' '.join(trace.name)
 for tool in ['FASTQC','FASTP','SALMON_INDEX','SALMON_QUANT','MULTIQC']:assert tool in tasks
 q=list((t/'nf-results').rglob('quant.sf'));assert len(q)==1
 quant=pd.read_csv(q[0],sep='\t');meta=json.loads((q[0].parent/'aux_info/meta_info.json').read_text())
 assert len(quant)==s['transcripts']>5000 and (quant.TPM>=0).all() and (quant.NumReads>=0).all()
 assert abs(float(quant.TPM.sum())-s['TPMSum'])<1e-6 and abs(quant.TPM.sum()-1e6)<2
 assert abs(float(quant.NumReads.sum())-s['assignedReadSum'])<1e-6
 assert np.isfinite(quant[['Length','EffectiveLength','TPM','NumReads']].to_numpy()).all()
 assert meta['num_processed']==s['salmonProcessed']==s['afterTrimmingReads']
 assert meta['num_mapped']==s['salmonMapped'] and 0<s['salmonMapped']<=s['afterTrimmingReads']<=s['inputReads']==1039872
 assert abs(meta['percent_mapped']-100*meta['num_mapped']/meta['num_processed'])<.01
 raw_qc=[]
 for f in (t/'nf-results').rglob('*_fastqc.zip'):
  with zipfile.ZipFile(f) as z:
   data=z.read(next(n for n in z.namelist() if n.endswith('/fastqc_data.txt'))).decode()
   total=int(next(line.split('\t')[1] for line in data.splitlines() if line.startswith('Total Sequences\t')))
   raw_qc.append(total)
 assert 1039872 in raw_qc
 assert len(list((t/'dependency-locks').glob('*.txt')))==16
 assert any('multiqc' in f.name.lower() and f.suffix=='.html' for f in (t/'nf-results').rglob('*'))
 for original,published in [('transcript-abundance.png','published-transcript-abundance.png'),('library-qc.png','published-library-qc.png')]:
  assert (t/original).read_bytes()==(out/published).read_bytes()
  with Image.open(out/published) as image:assert image.width>=1500 and image.height>=900;image.verify()
print(json.dumps({'status':'success','fullLibraryReads':1039872,'innerCompletedTasks':s['run']['innerCompletedTasks'],'quantifiedTranscripts':s['transcripts'],'salmonMapped':s['salmonMapped'],'realFigures':2,'differentialExpressionClaimed':False}))
