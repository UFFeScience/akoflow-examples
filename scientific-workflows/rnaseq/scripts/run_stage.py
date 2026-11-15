import argparse,csv,gzip,hashlib,json,os,shutil,subprocess,tarfile,tempfile,time,urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--output',default='.');args=p.parse_args()
out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True);app=Path('/app')
manifest=json.loads((app/'data/input-verification.json').read_text())
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(name,value):(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def pack(path,items):
 with tarfile.open(path,'w:gz',dereference=True) as t:
  for f,name in items:t.add(f,arcname=name,recursive=False)
def unpack(path,target):
 with tarfile.open(path) as t:
  for m in t.getmembers():
   assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
   f=target/m.name;f.parent.mkdir(parents=True,exist_ok=True)
   with t.extractfile(m) as s,f.open('wb') as d:shutil.copyfileobj(s,d)
if args.stage=='acquire':
 with tempfile.TemporaryDirectory() as temp:
  temp=Path(temp)
  for r in manifest['files']:
   f=temp/r['filename']
   for attempt in range(4):
    try:
     with urllib.request.urlopen(r['url'],timeout=120) as s,f.open('wb') as d:shutil.copyfileobj(s,d)
     assert f.stat().st_size==r['bytes'] and sha(f)==r['sha256'];break
    except Exception:
     if attempt==3:raise
     time.sleep(2)
   print('Verified full scientific input:',r['filename'],flush=True)
  pack(out/'observations.tar.gz',[(temp/r['filename'],r['filename']) for r in manifest['files']])
 save('acquisition.json',manifest)
elif args.stage=='pipeline':
 data=out/'observations';data.mkdir(exist_ok=True);unpack(out/'observations.tar.gz',data)
 for r in manifest['files']:assert sha(data/r['filename'])==r['sha256']
 reads=bases=0
 with gzip.open(data/'SRR10143877.fastq.gz','rt') as f:
  while header:=f.readline():
   sequence=f.readline().strip();separator=f.readline();quality=f.readline().strip()
   assert header.startswith('@') and separator.startswith('+') and len(sequence)==len(quality)>0
   reads+=1;bases+=len(sequence)
 assert reads==manifest['reads']==1039872 and bases==manifest['bases']==53033472
 (out/'samplesheet.csv').write_text('sample,fastq_1,fastq_2,strandedness\nSRR10143877,'+str(data/'SRR10143877.fastq.gz')+',,unstranded\n')
 params={'input':str(out/'samplesheet.csv'),'outdir':str(out/'nf-results'),'fasta':str(data/'genome.fa.gz'),'gtf':str(data/'genes.gtf.gz'),'transcript_fasta':str(data/'transcripts.fa.gz'),'igenomes_ignore':True,'trimmer':'fastp','save_trimmed':True,'save_reference':True,'salmon_quant_libtype':'U'}
 save('params.json',params)
 command=['nextflow','run','/app/upstream/rnaseq','-offline','-profile','rapid_quant','-c','/app/config/akoflow-local.config','-params-file',str(out/'params.json'),'-work-dir',str(out/'nf-work'),'-with-trace',str(out/'nextflow-trace.tsv'),'-with-report',str(out/'nextflow-report.html'),'-with-timeline',str(out/'nextflow-timeline.html')]
 env=dict(os.environ,NXF_OFFLINE='true',NXF_ANSI_LOG='false',NXF_OPTS='-Xms256m -Xmx2g')
 with (out/'nextflow-console.log').open('w') as log:
  result=subprocess.run(command,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode:
  print((out/'nextflow-console.log').read_text()[-12000:],flush=True);raise SystemExit(result.returncode)
 trace=pd.read_csv(out/'nextflow-trace.tsv',sep='\t');assert len(trace)>5 and (trace.status=='COMPLETED').all() and (trace.exit.astype(str)=='0').all()
 files=[(f,'nf-results/'+str(f.relative_to(out/'nf-results'))) for f in (out/'nf-results').rglob('*') if f.is_file()]
 for name in ['nextflow-trace.tsv','nextflow-report.html','nextflow-timeline.html','nextflow-console.log','params.json','samplesheet.csv']:files.append((out/name,name))
 for f in sorted(Path('/opt/nf-env-locks').glob('*.txt')):files.append((f,'dependency-locks/'+f.name))
 files.append((app/'data/input-verification.json','input-verification.json'))
 save('pipeline-run.json',{'status':'success','upstreamRepository':'https://github.com/nf-core/rnaseq','upstreamVersion':'3.27.0','upstreamCommit':'a1fcdddd3b826fe46eb46f0479f2ff8a7815af05','nextflowVersion':'25.10.4','profile':'rapid_quant','executor':'local within one native Akoflow pipeline activity','innerCompletedTasks':len(trace),'inputReads':reads,'inputBases':bases,'subsampledForQuantification':False,'libraryType':'single-end unstranded U','singleEndFragmentLengthModel':'Salmon default fragment length prior; not independently measured from paired fragments','command':command})
 files.append((out/'pipeline-run.json','pipeline-run.json'));pack(out/'pipeline-results.tar.gz',files)
 for directory in ['nf-work','nf-results','observations','.nextflow']:
  if (out/directory).exists():shutil.rmtree(out/directory)
 assert not any(f.is_symlink() for f in out.rglob('*')), 'Only regular retained artifacts may cross native activity boundaries'
elif args.stage=='visuals':
 import matplotlib.pyplot as plt
 with tempfile.TemporaryDirectory() as temp:
  temp=Path(temp);unpack(out/'pipeline-results.tar.gz',temp)
  quantpaths=list((temp/'nf-results').rglob('quant.sf'));assert len(quantpaths)==1,quantpaths
  quant=pd.read_csv(quantpaths[0],sep='\t');assert len(quant)>5000
  metapath=quantpaths[0].parent/'aux_info/meta_info.json';meta=json.loads(metapath.read_text())
  fastps=[]
  for f in (temp/'nf-results').rglob('*.json'):
   value=json.loads(f.read_text())
   if 'summary' in value and 'before_filtering' in value['summary']:fastps.append(value)
  assert len(fastps)==1
  fastp=fastps[0]['summary'];raw=fastp['before_filtering']['total_reads'];retained=fastp['after_filtering']['total_reads']
  assert raw==1039872 and meta['num_processed']==retained and 0<meta['num_mapped']<=retained<=raw
  assert np.isfinite(quant[['Length','EffectiveLength','TPM','NumReads']].to_numpy()).all()
  assert (quant.TPM>=0).all() and abs(quant.TPM.sum()-1e6)<2
  top=quant.nlargest(20,'TPM').iloc[::-1]
  fig,axes=plt.subplots(1,2,figsize=(14,8));axes[0].barh(top.Name,top.TPM,color='#333333');axes[0].set(xlabel='Transcripts per million (TPM)',title='Top 20 quantified yeast transcripts')
  positive=quant.loc[quant.TPM>0,'TPM'];axes[1].hist(np.log10(positive),bins=40,color='#555555');axes[1].set(xlabel='log10(TPM), positive transcripts',ylabel='Transcript count',title='Actual abundance distribution')
  fig.suptitle('RNA-seq — complete real library SRR10143877');fig.tight_layout();fig.savefig(out/'transcript-abundance.png',dpi=150);plt.close(fig)
  fig,ax=plt.subplots(figsize=(10,6));labels=['Raw reads','After fastp','Salmon processed','Salmon mapped'];values=[raw,retained,meta['num_processed'],meta['num_mapped']];bars=ax.bar(labels,values,color=['#777777','#555555','#333333','#111111'])
  for bar,value in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,value,str(value),ha='center',va='bottom')
  ax.set(ylabel='Single-end reads / fragments',title='Actual full-library retention and quantification');ax.set_ylim(0,raw*1.15);fig.tight_layout();fig.savefig(out/'library-qc.png',dpi=150);plt.close(fig)
  run=json.loads((temp/'pipeline-run.json').read_text())
  report={'status':'success','run':run,'inputReads':raw,'afterTrimmingReads':retained,'salmonProcessed':meta['num_processed'],'salmonMapped':meta['num_mapped'],'salmonMappingPercent':meta['percent_mapped'],'transcripts':len(quant),'positiveTPMTranscripts':int((quant.TPM>0).sum()),'TPMSum':float(quant.TPM.sum()),'assignedReadSum':float(quant.NumReads.sum()),'singleLibraryOnly':True,'differentialExpressionClaimed':False,'interpretation':'Single-library RNA abundance and QC. No replicate contrasts, differential expression or organism-wide condition effects are inferred. Transcript TPMs depend on the reference, strandedness assumption and single-end fragment-length prior.'}
  for name in ['transcript-abundance.png','library-qc.png']:shutil.copyfile(out/name,temp/name)
  report['resultSHA256']={str(f.relative_to(temp)):sha(f) for f in temp.rglob('*') if f.is_file()}
  save('derived-summary.json',report);shutil.copyfile(out/'derived-summary.json',temp/'rnaseq-summary.json')
  pack(out/'derived-results.tar.gz',[(f,str(f.relative_to(temp))) for f in temp.rglob('*') if f.is_file()])
elif args.stage=='package':
 for source,dest in [('derived-summary.json','rnaseq-summary.json'),('derived-results.tar.gz','rnaseq-results.tar.gz'),('transcript-abundance.png','published-transcript-abundance.png'),('library-qc.png','published-library-qc.png')]:shutil.copyfile(out/source,out/dest)
else:raise SystemExit('Unknown stage')
save('stage-'+args.stage+'.json',{'status':'success','stage':args.stage})
