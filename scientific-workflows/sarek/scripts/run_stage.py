import argparse,collections,gzip,hashlib,json,os,shutil,subprocess,tarfile,tempfile,time,urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True);parser.add_argument('--output',default='.');args=parser.parse_args()
out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True);app=Path('/app')
manifest=json.loads((app/'data/input-verification.json').read_text());environments=json.loads((app/'data/selected-environments.json').read_text())
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
def save(name,value):(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def pack(path,files):
 with tarfile.open(path,'w' if str(path).endswith('.tar') else 'w:gz',dereference=True) as archive:
  for f,name in files:archive.add(f,arcname=name,recursive=False)
def unpack(path,target):
 with tarfile.open(path) as archive:
  for member in archive.getmembers():
   assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
   destination=target/member.name;destination.parent.mkdir(parents=True,exist_ok=True)
   with archive.extractfile(member) as source,destination.open('wb') as stream:shutil.copyfileobj(source,stream)
def binary(module,name):return str(Path(next(e['prefix'] for e in environments if e['module']==module))/'bin'/name)
if args.stage=='acquire':
 with tempfile.TemporaryDirectory() as temporary:
  temporary=Path(temporary)
  for record in manifest['files']:
   target=temporary/record['filename']
   for attempt in range(4):
    try:
     with urllib.request.urlopen(record['url'],timeout=180) as source,target.open('wb') as stream:shutil.copyfileobj(source,stream,4*1024*1024)
     assert target.stat().st_size==record['bytes'] and digest(target)==record['sha256'];break
    except Exception:
     if attempt==3:raise
     time.sleep(3)
   print('Verified full frozen real input:',record['filename'],record['bytes'],flush=True)
  pack(out/'observations.tar',[(temporary/r['filename'],r['filename']) for r in manifest['files']])
 save('acquisition.json',manifest)
elif args.stage=='pipeline':
 data=out/'observations';data.mkdir(exist_ok=True);unpack(out/'observations.tar',data)
 for record in manifest['files']:assert digest(data/record['filename'])==record['sha256']
 with gzip.open(data/'reference.fa.gz','rb') as source,(data/'reference.fa').open('wb') as stream:shutil.copyfileobj(source,stream,4*1024*1024)
 assert digest(data/'reference.fa')==manifest['sourceReference']['sha256']
 samtools=binary('samtools/faidx','samtools');bam=data/'HG002.chr20-10-11Mb.bam'
 subprocess.run([samtools,'quickcheck','-v',str(bam)],check=True)
 count=int(subprocess.check_output([samtools,'view','-c',str(bam)],text=True));assert count==manifest['selectedAlignments']==280468
 (out/'samplesheet.csv').write_text('patient,sample,bam,bai\nHG002,HG002,'+str(bam)+','+str(data/'HG002.chr20-10-11Mb.bam.bai')+'\n')
 params={'input':str(out/'samplesheet.csv'),'outdir':str(out/'nf-results'),'fasta':str(data/'reference.fa'),'igenomes_ignore':True,'genome':None,'step':'variant_calling','tools':'haplotypecaller','intervals':str(data/'intervals.bed'),'save_reference':True,'skip_tools':'haplotypecaller_filter'}
 save('params.json',params)
 command=['nextflow','run','/app/upstream/sarek','-offline','-c','/app/config/akoflow-local.config','-params-file',str(out/'params.json'),'-work-dir',str(out/'nf-work'),'-with-trace',str(out/'nextflow-trace.tsv'),'-with-report',str(out/'nextflow-report.html'),'-with-timeline',str(out/'nextflow-timeline.html')]
 environment=dict(os.environ,NXF_OFFLINE='true',NXF_ANSI_LOG='false',NXF_OPTS='-Xms256m -Xmx2g')
 with (out/'nextflow-console.log').open('w') as stream:result=subprocess.run(command,cwd=out,env=environment,stdout=stream,stderr=subprocess.STDOUT)
 console=(out/'nextflow-console.log').read_text()
 if result.returncode:print(console[-14000:],flush=True);raise SystemExit(result.returncode)
 assert 'Creating env using' not in console, 'Every selected scientific tool must be preinstalled in the measured image'
 trace=pd.read_csv(out/'nextflow-trace.tsv',sep='\t');assert len(trace)>5 and (trace.status=='COMPLETED').all() and (trace.exit.astype(str)=='0').all()
 candidates=[p for p in (out/'nf-results').rglob('*.vcf.gz') if 'variant_calling' in p.parts and 'haplotypecaller' in p.parts]
 assert len(candidates)==1,[str(p) for p in candidates]
 bcftools=binary('bcftools/norm','bcftools')
 validation=subprocess.run([bcftools,'norm','--check-ref','e','--fasta-ref',str(data/'reference.fa'),'-Ou','-o','/dev/null',str(candidates[0])],capture_output=True,text=True,check=True)
 save('reference-validation.json',{'status':'success','method':'bcftools norm --check-ref e against the complete frozen compatible reference; normalization is checked without replacing the original Sarek VCF','stderr':validation.stderr.strip(),'variantPath':str(candidates[0].relative_to(out))})
 with (out/'reference-region.fa').open('w') as stream:subprocess.run([samtools,'faidx',str(data/'reference.fa'),'chr20:9999001-11001000'],stdout=stream,check=True)
 save('pipeline-run.json',{'status':'success','upstreamRepository':'https://github.com/nf-core/sarek','upstreamVersion':'3.12.0','upstreamCommit':'786a11bb4f989751d1c4bb87908ffc6096635ff3','nextflowVersion':'25.10.4','step':'variant_calling','caller':'GATK HaplotypeCaller','innerCompletedTasks':len(trace),'selectedAlignments':count,'regionBED0Based':manifest['regionBED0Based'],'scientificDependenciesPreinstalled':True,'command':command,'interpretation':'Raw unfiltered diploid germline calls on the stated 1Mb region from a frozen prealigned public HG002 subset. No new mapping, BQSR, whole-genome calling, CNN tranche calibration or clinical accuracy is claimed. Optional haplotypecaller_filter is disabled explicitly; no appropriate external known-site calibration set is supplied for this bounded profile.'})
 files=[(p,'nf-results/'+str(p.relative_to(out/'nf-results'))) for p in (out/'nf-results').rglob('*') if p.is_file()]
 for name in ['nextflow-trace.tsv','nextflow-report.html','nextflow-timeline.html','nextflow-console.log','params.json','samplesheet.csv','pipeline-run.json','reference-validation.json','reference-region.fa']:files.append((out/name,name))
 for prefix in sorted(set(e['prefix'] for e in environments)):
  name=Path(prefix).name+'.txt';files.append((Path('/opt/nf-env-locks')/name,'dependency-locks/'+name))
 for name in ['HG002.chr20-10-11Mb.bam','HG002.chr20-10-11Mb.bam.bai','intervals.bed']:files.append((data/name,'inputs/'+name))
 files.append((app/'data/input-verification.json','input-verification.json'));files.append((app/'data/selected-environments.json','selected-environments.json'))
 pack(out/'pipeline-results.tar.gz',files)
 for directory in ['nf-work','nf-results','observations','.nextflow']:
  if (out/directory).exists():shutil.rmtree(out/directory)
 assert not any(p.is_symlink() for p in out.rglob('*'))
elif args.stage=='visuals':
 import matplotlib.pyplot as plt
 with tempfile.TemporaryDirectory() as temporary:
  temporary=Path(temporary);unpack(out/'pipeline-results.tar.gz',temporary)
  paths=[p for p in (temporary/'nf-results').rglob('*.vcf.gz') if 'variant_calling' in p.parts and 'haplotypecaller' in p.parts];assert len(paths)==1
  rows=[];types=collections.Counter();genotypes=collections.Counter();vafs=[];sample=None
  with gzip.open(paths[0],'rt') as stream:
   for line in stream:
    if line.startswith('##'):continue
    fields=line.rstrip('\n').split('\t')
    if line.startswith('#CHROM'):
     assert len(fields)==10 and fields[-1]=='HG002';sample=fields[-1];continue
    chrom,pos,identifier,ref,alt,qual,filter_,info,format_,value=fields
    values=dict(zip(format_.split(':'),value.split(':')));gt=values.get('GT','.');genotypes[gt]+=1
    ad=values.get('AD','.');depth=values.get('DP','.')
    for allele in alt.split(','):
     types['SNP' if len(ref)==len(allele)==1 else 'INDEL' if len(ref)!=len(allele) else 'MNV']+=1
    if ad!='.' and all(x.isdigit() for x in ad.split(',')):
     observed=[int(x) for x in ad.split(',')]
     if sum(observed)>0:vafs.extend(n/sum(observed) for n in observed[1:])
    rows.append({'chrom':chrom,'pos':int(pos),'ref':ref,'alt':alt,'qual':float(qual) if qual!='.' else None,'filter':filter_,'GT':gt,'DP':depth,'AD':ad})
  assert sample=='HG002'
  frame=pd.DataFrame(rows,columns=['chrom','pos','ref','alt','qual','filter','GT','DP','AD']);frame.to_csv(out/'variant-observations.tsv',sep='\t',index=False)
  fig,axes=plt.subplots(2,2,figsize=(12,9))
  labels=['SNP','INDEL','MNV'];axes[0,0].bar(labels,[types[x] for x in labels],color='#333333');axes[0,0].set(title='Actual alternate-allele classes',ylabel='Alleles')
  axes[0,1].hist(frame.pos if len(frame) else [],bins=np.linspace(10000000,11000001,51),color='#444444');axes[0,1].set(title='Raw call positions in the selected region',xlabel='GRCh38 chr20 position',ylabel='VCF records')
  quality=frame.qual.dropna().to_numpy(dtype=float);axes[1,0].hist(np.log10(quality[quality>=0]+1),bins=35,color='#555555');axes[1,0].set(title='Observed caller quality distribution',xlabel='log10(QUAL + 1)',ylabel='VCF records')
  axes[1,1].hist(vafs,bins=np.linspace(0,1,31),color='#222222');axes[1,1].set(title='Observed alternate-read fractions',xlabel='ALT depth / total AD depth',ylabel='Alternate alleles')
  if not vafs:axes[1,1].text(.5,.5,'No observed allele depths',ha='center',transform=axes[1,1].transAxes)
  fig.suptitle('Sarek — real HG002 regional raw germline calls');fig.tight_layout();fig.savefig(out/'regional-variants.png',dpi=150);plt.close(fig)
  fig,ax=plt.subplots(figsize=(10,5));items=sorted(genotypes.items());ax.bar([k for k,_ in items],[n for _,n in items],color='#333333');ax.set(title='Actual genotype observations — raw regional calls',xlabel='VCF genotype',ylabel='Records');fig.tight_layout();fig.savefig(out/'genotype-observations.png',dpi=150);plt.close(fig)
  report={'status':'success','sample':sample,'regionBED0Based':manifest['regionBED0Based'],'selectedAlignments':manifest['selectedAlignments'],'variantRecords':len(frame),'alternateAlleleClasses':dict(types),'genotypeCounts':dict(genotypes),'observedADAlleleFractions':len(vafs),'rawUnfilteredCalls':True,'wholeGenomeClaimed':False,'clinicalAccuracyClaimed':False,'pipelineRun':json.loads((temporary/'pipeline-run.json').read_text()),'referenceValidation':json.loads((temporary/'reference-validation.json').read_text()),'interpretation':'Exploratory raw regional variant calls from a public benchmark sample, not a clinically validated or whole-genome call set. Counts retain original VCF fields and optional quality filters have not been fabricated.'}
  for name in ['variant-observations.tsv','regional-variants.png','genotype-observations.png']:shutil.copyfile(out/name,temporary/name)
  report['resultSHA256']={str(p.relative_to(temporary)):digest(p) for p in temporary.rglob('*') if p.is_file()}
  save('derived-summary.json',report);shutil.copyfile(out/'derived-summary.json',temporary/'sarek-summary.json')
  pack(out/'derived-results.tar.gz',[(p,str(p.relative_to(temporary))) for p in temporary.rglob('*') if p.is_file()])
elif args.stage=='package':
 for source,destination in [('derived-summary.json','sarek-summary.json'),('derived-results.tar.gz','sarek-results.tar.gz'),('regional-variants.png','published-regional-variants.png'),('genotype-observations.png','published-genotype-observations.png')]:shutil.copyfile(out/source,out/destination)
else:raise SystemExit('Unknown stage')
save('stage-'+args.stage+'.json',{'status':'success','stage':args.stage})
