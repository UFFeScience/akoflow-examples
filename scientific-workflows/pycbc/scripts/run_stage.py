import argparse,collections,gzip,hashlib,json,math,shutil,tarfile,tempfile,urllib.request
from pathlib import Path
import h5py
import numpy as np
from scipy.signal import find_peaks
from pycbc.types import TimeSeries
from pycbc.filter import highpass,resample_to_delta_t,matched_filter
from pycbc.psd import welch,interpolate,inverse_spectrum_truncation
from pycbc.waveform import get_fd_waveform

p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--detector',choices=['H1','L1']);p.add_argument('--output',default='.');a=p.parse_args()
out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);app=Path('/app');manifest=json.loads((app/'data/input-verification.json').read_text());profile=json.loads((app/'data/analysis.json').read_text())
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
def save(name,value):(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def pack(path,files):
 with tarfile.open(path,'w' if str(path).endswith('.tar') else 'w:gz',dereference=True) as t:
  for f,name in files:t.add(f,arcname=name,recursive=False)
def unpack(path,target):
 with tarfile.open(path) as t:
  for m in t.getmembers():
   assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
   f=target/m.name;f.parent.mkdir(parents=True,exist_ok=True)
   with t.extractfile(m) as s,f.open('wb') as d:shutil.copyfileobj(s,d)
def make_template(row,delta_f,length):
 hp,_=get_fd_waveform(approximant=profile['approximant'],mass1=row['mass1'],mass2=row['mass2'],spin1z=0,spin2z=0,f_lower=profile['flow'],f_final=profile['fhigh'],delta_f=delta_f)
 hp.resize(length);return hp
def load_condition(detector,target):
 unpack(out/(detector+'-condition.tar.gz'),target)
 meta=json.loads((target/(detector+'-condition.json')).read_text());x=np.load(target/(detector+'-condition.npz'))
 strain=TimeSeries(x['strain'],delta_t=1/profile['sampleRate'],epoch=meta['epoch'])
 from pycbc.types import FrequencySeries
 psd=FrequencySeries(x['psd'],delta_f=1/strain.duration)
 return strain,psd,meta,x
if a.stage=='acquire':
 with tempfile.TemporaryDirectory() as temp:
  temp=Path(temp)
  for r in manifest['files']:
   f=temp/r['filename']
   with urllib.request.urlopen(r['url'],timeout=180) as s,f.open('wb') as d:shutil.copyfileobj(s,d,4*1024*1024)
   assert f.stat().st_size==r['bytes'] and sha(f)==r['sha256']
   print('Verified complete observed detector strain:',r['detector'],r['bytes'],flush=True)
  pack(out/'observations.tar',[(temp/r['filename'],r['filename']) for r in manifest['files']])
 save('acquisition.json',manifest)
elif a.stage=='bank':
 length=int((4096-4)*profile['sampleRate']);df=1/(4096-4);rows=[]
 for mass1 in profile['masses']:
  for mass2 in profile['masses']:
   if mass1<mass2:continue
   row={'id':len(rows),'mass1':mass1,'mass2':mass2};hp=make_template(row,df,length//2+1)
   assert np.isfinite(hp.numpy()).all() and np.abs(hp.numpy()).max()>0
   row['waveformSHA256']=hashlib.sha256(hp.numpy().tobytes()).hexdigest();rows.append(row)
 assert len(rows)==66
 save('template-bank.json',{'templates':rows,'approximant':profile['approximant'],'spins':[0,0],'deltaF':df,'frequencyBins':length//2+1,'minimalMatchGuarantee':False,'interpretation':'Deterministic non-exhaustive high-mass binary-black-hole grid; not a stochastic minimal-match bank or a full compact-binary population search.'})
elif a.stage=='condition':
 d=a.detector
 with tempfile.TemporaryDirectory() as temp:
  temp=Path(temp);unpack(out/'observations.tar',temp);f=temp/(d+'-strain.hdf5')
  assert sha(f)==next(r['sha256'] for r in manifest['files'] if r['detector']==d)
  with h5py.File(f) as h:
   raw=h['strain/Strain'][:];epoch=float(h['meta/GPSstart'][()]);rate=1/float(h['strain/Strain'].attrs['Xspacing']);assert len(raw)==16777216 and rate==4096 and np.isfinite(raw).all()
   dq=h['quality/simple/DQmask'][:];names=[x.decode() for x in h['quality/simple/DQShortnames'][:]]
   inj=h['quality/injections/Injmask'][:];inames=[x.decode() for x in h['quality/injections/InjShortnames'][:]]
  require=sum(1<<names.index(n) for n in profile['requiredDQ']);ncbc=1<<inames.index('NO_CBC_HW_INJ');valid=((dq&require)==require)&((inj&ncbc)==ncbc)
  ts=TimeSeries(raw,delta_t=1/rate,epoch=epoch);ts=highpass(ts,15);ts=resample_to_delta_t(ts,1/profile['sampleRate']);ts=ts.crop(2,2)
  psd=welch(ts,seg_len=4*profile['sampleRate'],seg_stride=2*profile['sampleRate'],avg_method='median');psd=interpolate(psd,1/ts.duration);psd=inverse_spectrum_truncation(psd,max_filter_len=4*profile['sampleRate'],low_frequency_cutoff=profile['flow'],trunc_method='hann')
  band=(psd.sample_frequencies.numpy()>=profile['flow'])&(psd.sample_frequencies.numpy()<=profile['fhigh']);assert np.isfinite(psd.numpy()[band]).all() and (psd.numpy()[band]>0).all()
  np.savez_compressed(out/(d+'-condition.npz'),strain=ts.numpy(),psd=psd.numpy(),dq=dq,injections=inj,validSeconds=valid)
  save(d+'-condition.json',{'status':'success','detector':d,'rawSamples':len(raw),'rawEpoch':epoch,'rawSampleRate':rate,'epoch':float(ts.start_time),'samples':len(ts),'sampleRate':profile['sampleRate'],'durationSeconds':float(ts.duration),'validRawSeconds':int(valid.sum()),'dqFlags':names,'injectionFlags':inames,'requiredDQ':profile['requiredDQ'],'requiredInjectionVeto':'NO_CBC_HW_INJ','allInjectionMaskValues':[int(x) for x in np.unique(inj)],'psdMethod':'Welch median, 4s segments/2s stride; interpolate and 4s Hann inverse-spectrum truncation','resampling':'PyCBC Butterworth antialias resampling from 4096 to 1024Hz; 15Hz highpass; 2s trimmed at each edge','filterBandHz':[profile['flow'],profile['fhigh']]})
  pack(out/(d+'-condition.tar.gz'),[(out/(d+'-condition.npz'),d+'-condition.npz'),(out/(d+'-condition.json'),d+'-condition.json')])
elif a.stage=='filter':
 d=a.detector;bank=json.loads((out/'template-bank.json').read_text());triggers=[];summaries=[];envelopes=[]
 with tempfile.TemporaryDirectory() as temp:
  strain,psd,meta,x=load_condition(d,Path(temp));edge=8*profile['sampleRate'];end=len(strain)-edge
  for row in bank['templates']:
   hp=make_template(row,psd.delta_f,len(psd));assert hashlib.sha256(hp.numpy().tobytes()).hexdigest()==row['waveformSHA256']
   snr=matched_filter(hp,strain,psd=psd,low_frequency_cutoff=profile['flow'],high_frequency_cutoff=profile['fhigh']);values=np.abs(snr.numpy());samples=np.arange(edge,end);gps=float(snr.start_time)+samples/profile['sampleRate'];quality=(np.floor(gps-meta['rawEpoch']).astype(int));usable=x['validSeconds'][quality];peaks,_=find_peaks(values[edge:end],height=profile['threshold'],distance=int(.1*profile['sampleRate']));peaks=peaks+edge
   for index in peaks:
    time=float(snr.start_time)+int(index)/profile['sampleRate'];q=int(math.floor(time-meta['rawEpoch']))
    if x['validSeconds'][q]:triggers.append({'template':row['id'],'gps':time,'snr':float(values[index]),'phase':float(np.angle(snr[index]))})
   allowed=np.where(usable,values[edge:end],-np.inf);i=int(allowed.argmax())+edge;local=(np.abs(gps-manifest['catalogueGPS'])<=.5)&usable
   j=int(np.where(local,values[edge:end],-np.inf).argmax())+edge
   summaries.append({'template':row['id'],'globalGPS':float(snr.start_time)+i/profile['sampleRate'],'globalSNR':float(values[i]),'catalogueWindowGPS':float(snr.start_time)+j/profile['sampleRate'],'catalogueWindowSNR':float(values[j]),'waveformSHA256':row['waveformSHA256']})
   envelopes.append(values[edge:end].reshape(-1,profile['sampleRate']).max(axis=1).astype(np.float32))
   print(d,'completed physical template',row['id'],row['mass1'],row['mass2'],flush=True)
  np.savez_compressed(out/(d+'-snr-envelopes.npz'),maximumSNRPerSecond=np.stack(envelopes),epoch=float(strain.start_time)+8)
  save(d+'-triggers.json',{'detector':d,'threshold':profile['threshold'],'clusterSecondsPerTemplate':.1,'edgeCropSeconds':8,'analysisEpoch':float(strain.start_time)+8,'analysisDurationSeconds':float(strain.duration)-16,'templates':len(summaries),'triggers':triggers,'templatePeaks':summaries})
elif a.stage=='coincidence':
 h=json.loads((out/'H1-triggers.json').read_text());l=json.loads((out/'L1-triggers.json').read_text());allrows=[];slides=[]
 def pairs(offset,background=False):
  found=[]
  for template in range(66):
   hs=[r for r in h['triggers'] if r['template']==template];ls=sorted([r for r in l['triggers'] if r['template']==template],key=lambda r:r['gps']);times=np.array([r['gps']+offset for r in ls])
   for one in hs:
    if background and abs(one['gps']-manifest['catalogueGPS'])<=1:continue
    low,high=np.searchsorted(times,[one['gps']-.015,one['gps']+.015],side='left')
    for i in range(low,high):
     two=ls[i]
     if background and abs(two['gps']-manifest['catalogueGPS'])<=1:continue
     found.append({'template':template,'gps':(one['gps']+two['gps']+offset)/2,'H1GPS':one['gps'],'L1GPS':two['gps'],'lagSeconds':one['gps']-two['gps']-offset,'H1SNR':one['snr'],'L1SNR':two['snr'],'networkSNR':math.hypot(one['snr'],two['snr'])})
  return found
 def cluster(rows):
  accepted=[]
  for row in sorted(rows,key=lambda r:r['networkSNR'],reverse=True):
   if all(abs(row['gps']-other['gps'])>1 for other in accepted):accepted.append(row)
  return sorted(accepted,key=lambda r:r['gps'])
 allrows=pairs(0);clustered=cluster(allrows)
 for offset in profile['timeSlidesSeconds']:
  rows=cluster(pairs(offset,True));slides.append({'offsetSeconds':offset,'nominalOverlapSeconds':max(0,min(h['analysisDurationSeconds'],l['analysisDurationSeconds'])-abs(offset)-2),'coincidences':rows})
 near=[r for r in clustered if abs(r['gps']-manifest['catalogueGPS'])<=.5];selected=max(near,key=lambda r:r['networkSNR']) if near else (max(clustered,key=lambda r:r['networkSNR']) if clustered else None)
 save('coincidences.json',{'status':'success','templateCount':66,'coincidenceWindowSeconds':.015,'clusterWindowSeconds':1,'zeroLagUnclustered':allrows,'zeroLagClustered':clustered,'timeSlides':slides,'selectedForFollowup':selected,'selectionReason':'Highest network SNR coincidence in the explicitly declared catalogue +/-0.5s followup window; if absent, global maximum. This is not a blind discovery claim.','significance':'Exploratory network SNR with sparse non-exhaustive mass grid and finite time shifts. No calibrated false-alarm rate/probability, chi-square reweighting, population completeness or parameter posterior is claimed.','backgroundKnownEventExclusionSeconds':1})
elif a.stage=='figures':
 import matplotlib.pyplot as plt
 bank=json.loads((out/'template-bank.json').read_text());coinc=json.loads((out/'coincidences.json').read_text());selected=coinc['selectedForFollowup'];row=bank['templates'][selected['template'] if selected else 0];public=[];diagnostics={}
 with tempfile.TemporaryDirectory() as temporary:
  temporary=Path(temporary);fig,axes=plt.subplots(3,1,figsize=(12,11));event=manifest['catalogueGPS']
  for d in ['H1','L1']:
   strain,psd,meta,x=load_condition(d,temporary);hp=make_template(row,psd.delta_f,len(psd));snr=matched_filter(hp,strain,psd=psd,low_frequency_cutoff=profile['flow'],high_frequency_cutoff=profile['fhigh'])
   np.savez_compressed(out/(d+'-followup.npz'),snr=snr.numpy(),epoch=float(snr.start_time),deltaT=float(snr.delta_t),template=row['id'])
   sf=strain.to_frequencyseries();white=(sf/psd**.5).to_timeseries();smooth=highpass(white,35);from pycbc.filter import lowpass
   smooth=lowpass(smooth,300);t=smooth.sample_times.numpy();window=np.abs(t-event)<.25;axes[0].plot(t[window]-event,smooth.numpy()[window],label=d,linewidth=.8)
   frequencies=psd.sample_frequencies.numpy();valid=(frequencies>=15)&(frequencies<=500);axes[1].loglog(frequencies[valid],np.sqrt(psd.numpy()[valid]),label=d)
   st=snr.sample_times.numpy();win=np.abs(st-event)<.5;axes[2].plot(st[win]-event,np.abs(snr.numpy()[win]),label=d)
   diagnostics[d]={'epoch':meta['epoch'],'conditionedSamples':meta['samples'],'rawSamples':meta['rawSamples'],'validRawSeconds':meta['validRawSeconds'],'rawQualityMaskValues':[int(v) for v in np.unique(x['dq'])],'rawInjectionMaskValues':[int(v) for v in np.unique(x['injections'])]}
   public += [(temporary/(d+'-condition.npz'),d+'-condition.npz'),(temporary/(d+'-condition.json'),d+'-condition.json'),(out/(d+'-followup.npz'),d+'-followup.npz'),(out/(d+'-triggers.json'),d+'-triggers.json'),(out/(d+'-snr-envelopes.npz'),d+'-snr-envelopes.npz')]
  axes[0].set(title='Observed whitened/bandpassed strain — no display time shift or sign flip',xlabel='Seconds relative to catalogue GPS',ylabel='Whitened strain')
  axes[1].set(title='Estimated detector noise amplitude spectra',xlabel='Frequency (Hz)',ylabel='Strain / sqrt(Hz)')
  axes[2].set(title='Actual matched-filter SNR for the selected shared physical template',xlabel='Seconds relative to catalogue GPS',ylabel='Absolute SNR')
  for axis in axes:axis.legend();axis.grid(alpha=.2)
  fig.suptitle('PyCBC / LIGO — real GW150914 detector observations');fig.tight_layout();fig.savefig(out/'detector-analysis.png',dpi=150);plt.close(fig)
  fig,axes=plt.subplots(1,2,figsize=(12,5));zero=coinc['zeroLagClustered'];background=[r for slide in coinc['timeSlides'] for r in slide['coincidences']]
  axes[0].scatter([r['gps']-event for r in zero],[r['networkSNR'] for r in zero],s=20,color='#222222');axes[0].axvline(0,color='#777777',linestyle='--');axes[0].set(title='Measured zero-lag two-detector coincidences',xlabel='Seconds relative to catalogue GPS',ylabel='Network SNR')
  axes[1].hist([r['networkSNR'] for r in background],bins=20,color='#777777',label='Time shifts');axes[1].hist([r['networkSNR'] for r in zero],bins=20,histtype='step',color='black',label='Zero lag');axes[1].set(title='Exploratory coincident-score distributions',xlabel='Network SNR',ylabel='Clustered coincidence count');axes[1].legend();fig.tight_layout();fig.savefig(out/'coincidence-analysis.png',dpi=150);plt.close(fig)
  report={'status':'success','eventCatalogueGPS':event,'detectors':diagnostics,'physicalTemplateCount':66,'selectedTemplate':row,'coincidence':coinc,'syntheticObservedStrainAdded':False,'interpretation':'Targeted known-event reanalysis of full 4096s public H1/L1 observations, using all conditioned usable samples and a sparse non-exhaustive physical mass grid. Theoretical model templates are not added to observed strain. This does not reproduce the full PyCBC HTCondor survey, significance calibration or parameter estimation.'}
  for name in ['template-bank.json','coincidences.json','detector-analysis.png','coincidence-analysis.png']:public.append((out/name,name))
  public.append((out/'observations.tar','observations.tar'));public.append((app/'data/input-verification.json','input-verification.json'));public.append((app/'data/analysis.json','analysis.json'));public.append((Path('/opt/python-dependencies.lock'),'python-dependencies.lock'))
  report['resultSHA256']={name:sha(f) for f,name in public};save('derived-summary.json',report);public.append((out/'derived-summary.json','pycbc-summary.json'));pack(out/'derived-results.tar.gz',public)
elif a.stage=='package':
 for source,dest in [('derived-summary.json','pycbc-summary.json'),('derived-results.tar.gz','pycbc-results.tar.gz'),('detector-analysis.png','published-detector-analysis.png'),('coincidence-analysis.png','published-coincidence-analysis.png')]:shutil.copyfile(out/source,out/dest)
else:raise SystemExit('Unknown stage')
save('stage-'+a.stage+('-'+a.detector if a.detector else '')+'.json',{'status':'success','stage':a.stage,'detector':a.detector})
