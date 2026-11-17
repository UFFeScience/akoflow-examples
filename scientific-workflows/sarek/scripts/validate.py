import argparse,collections,gzip,hashlib,json,subprocess,tarfile,tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
parser=argparse.ArgumentParser();parser.add_argument('--definition',action='store_true');parser.add_argument('--output',default='/outputs');args=parser.parse_args()
app=Path('/app');m=json.loads((app/'data/input-verification.json').read_text());w=json.loads((app/'workflow.json').read_text());envs=json.loads((app/'data/selected-environments.json').read_text())
assert m['selectedAlignments']==280468 and m['regionBED0Based']==['chr20',10000000,11000000]
assert len(m['files'])==4 and sum(f['bytes'] for f in m['files'])==946022042
assert all((Path('/opt/nextflowhome/plugins')/name.replace('@','-')).is_dir() for name in ['nf-core-utils@0.4.0','nf-fgbio@1.0.0','nf-prov@1.7.0','nf-schema@2.7.2'])
assert len(w['spec']['activities'])==4 and len(envs)==24 and len(set(e['prefix'] for e in envs))==11
for e in envs:
 assert Path(e['prefix']).is_dir() and (Path('/opt/nf-env-locks')/(Path(e['prefix']).name+'.txt')).is_file()
 assert hashlib.sha256((app/'upstream/sarek'/e['modulePath']/'environment.yml').read_bytes()).hexdigest()==e['environmentSHA256']
assert hashlib.sha256((app/'upstream/sarek/nextflow.config').read_bytes()).hexdigest()==json.loads((app/'data/upstream.json').read_text())['nextflowConfigSHA256']
if args.definition:
 print(json.dumps({'status':'success','definitionOnly':True,'outerActivities':4,'originalPipeline':'nf-core/sarek 3.12.0','realRegionAlignments':280468,'selectedRecipes':24,'selectedEnvironments':11}));raise SystemExit
out=Path(args.output);report=json.loads((out/'sarek-summary.json').read_text());assert report['status']=='success' and report['rawUnfilteredCalls'] and not report['wholeGenomeClaimed'] and not report['clinicalAccuracyClaimed']
with tempfile.TemporaryDirectory() as temporary:
 target=Path(temporary)
 with tarfile.open(out/'sarek-results.tar.gz') as archive:
  assert len(archive.getnames())==len(set(archive.getnames()))
  assert set(archive.getnames())==set(report['resultSHA256'])|{'sarek-summary.json'}
  for member in archive.getmembers():
   assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
   f=target/member.name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(archive.extractfile(member).read())
 assert json.loads((target/'sarek-summary.json').read_text())==report
 for name,expected in report['resultSHA256'].items():assert hashlib.sha256((target/name).read_bytes()).hexdigest()==expected
 trace=pd.read_csv(target/'nextflow-trace.tsv',sep='\t');assert len(trace)==report['pipelineRun']['innerCompletedTasks']>5 and (trace.status=='COMPLETED').all() and (trace.exit.astype(str)=='0').all()
 for tool in ['GATK4_HAPLOTYPECALLER','GATK4_CREATESEQUENCEDICTIONARY','SAMTOOLS_FAIDX','CREATE_INTERVALS_BED','MULTIQC']:assert tool in ' '.join(trace.name)
 assert 'Creating env using' not in (target/'nextflow-console.log').read_text()
 params=json.loads((target/'params.json').read_text());assert params['step']=='variant_calling' and params['tools']=='haplotypecaller' and params['skip_tools']=='haplotypecaller_filter'
 assert report['referenceValidation']['status']=='success'
 samtools=str(Path(next(e['prefix'] for e in envs if e['module']=='samtools/faidx'))/'bin/samtools')
 bam=target/'inputs/HG002.chr20-10-11Mb.bam';subprocess.run([samtools,'quickcheck','-v',str(bam)],check=True)
 assert int(subprocess.check_output([samtools,'view','-c',str(bam)],text=True))==280468
 for record in m['files']:
  if record['filename']!='reference.fa.gz':assert hashlib.sha256((target/'inputs'/record['filename']).read_bytes()).hexdigest()==record['sha256']
 assert len(list((target/'dependency-locks').glob('*.txt')))==11
 sequence=''.join(l.strip() for l in (target/'reference-region.fa').read_text().splitlines() if not l.startswith('>'));assert len(sequence)==1002000
 paths=[p for p in (target/'nf-results').rglob('*.vcf.gz') if 'variant_calling' in p.parts and 'haplotypecaller' in p.parts];assert len(paths)==1
 rows=[];counts=collections.Counter();genotypes=collections.Counter();ad_values=0
 with gzip.open(paths[0],'rt') as stream:
  for line in stream:
   if line.startswith('##'):continue
   v=line.rstrip('\n').split('\t')
   if line.startswith('#CHROM'):assert len(v)==10 and v[-1]=='HG002';continue
   assert len(v)==10 and v[0]=='chr20';pos=int(v[1]);ref=v[3];offset=pos-9999001
   assert 0<=offset and offset+len(ref)<=len(sequence) and sequence[offset:offset+len(ref)].upper()==ref.upper()
   assert pos-1<11000000 and pos-1+len(ref)>10000000
   values=dict(zip(v[8].split(':'),v[9].split(':')));gt=values.get('GT','.');genotypes[gt]+=1
   for alt in v[4].split(','):counts['SNP' if len(ref)==len(alt)==1 else 'INDEL' if len(ref)!=len(alt) else 'MNV']+=1
   ad=values.get('AD','.')
   if ad!='.' and all(n.isdigit() for n in ad.split(',')) and sum(int(n) for n in ad.split(','))>0:ad_values+=len(ad.split(','))-1
   rows.append((v,values))
 table=pd.read_csv(target/'variant-observations.tsv',sep='\t',dtype=str,keep_default_na=False)
 assert len(rows)==len(table)==report['variantRecords'] and dict(counts)==report['alternateAlleleClasses'] and dict(genotypes)==report['genotypeCounts'] and ad_values==report['observedADAlleleFractions']
 for (v,values),(_,r) in zip(rows,table.iterrows()):
  assert list(r[['chrom','pos','ref','alt','filter','GT','DP','AD']])==[v[0],v[1],v[3],v[4],v[6],values.get('GT','.'),values.get('DP','.'),values.get('AD','.')]
  assert (v[5]=='.' and r['qual']=='') or np.isclose(float(r['qual']),float(v[5]))
 for original,published in [('regional-variants.png','published-regional-variants.png'),('genotype-observations.png','published-genotype-observations.png')]:
  assert (target/original).read_bytes()==(out/published).read_bytes()
  with Image.open(out/published) as image:assert image.width>=1500 and image.height>=750;image.verify()
 assert any('multiqc' in f.name.lower() and f.suffix=='.html' for f in (target/'nf-results').rglob('*'))
print(json.dumps({'status':'success','realRegionAlignments':280468,'variantRecords':report['variantRecords'],'innerCompletedTasks':report['pipelineRun']['innerCompletedTasks'],'allVCFReferenceAllelesVerified':True,'realFigures':2,'rawUnfilteredCalls':True,'wholeGenomeClaimed':False}))
