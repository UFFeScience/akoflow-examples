import argparse,collections,hashlib,json,tarfile,tempfile
from pathlib import Path
import h5py,numpy as np
from PIL import Image
from pycbc.types import TimeSeries,FrequencySeries
from pycbc.filter import matched_filter,highpass,resample_to_delta_t
from pycbc.psd import welch,interpolate,inverse_spectrum_truncation
from pycbc.waveform import get_fd_waveform
p=argparse.ArgumentParser();p.add_argument('--definition',action='store_true');p.add_argument('--output',default='/outputs');a=p.parse_args();app=Path('/app');m=json.loads((app/'data/input-verification.json').read_text());profile=json.loads((app/'data/analysis.json').read_text());workflow=json.loads((app/'workflow.json').read_text())
assert len(workflow['spec']['activities'])==9 and len(m['files'])==2 and m['rawSamplesPerDetector']==16777216
assert profile['sampleRate']==1024 and profile['masses']==list(range(20,71,5)) and profile['flow']==20 and profile['fhigh']==300
if a.definition:
 print(json.dumps({'status':'success','definitionOnly':True,'activities':9,'publicObservationSecondsPerDetector':4096,'physicalTemplates':66}));raise SystemExit
out=Path(a.output);report=json.loads((out/'pycbc-summary.json').read_text());assert report['status']=='success' and report['physicalTemplateCount']==66 and not report['syntheticObservedStrainAdded']
with tempfile.TemporaryDirectory() as temporary:
 t=Path(temporary)
 with tarfile.open(out/'pycbc-results.tar.gz') as archive:
  assert len(archive.getnames())==len(set(archive.getnames()))
  assert set(archive.getnames())==set(report['resultSHA256'])|{'pycbc-summary.json'}
  for member in archive.getmembers():
   assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
   f=t/member.name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(archive.extractfile(member).read())
 for name,expected in report['resultSHA256'].items():assert hashlib.sha256((t/name).read_bytes()).hexdigest()==expected
 with tarfile.open(t/'observations.tar') as archive:
  for member in archive.getmembers():
   assert member.name in ['H1-strain.hdf5','L1-strain.hdf5'] and member.isfile();(t/member.name).write_bytes(archive.extractfile(member).read())
 bank=json.loads((t/'template-bank.json').read_text());assert len(bank['templates'])==66 and len({(r['mass1'],r['mass2']) for r in bank['templates']})==66
 selected=report['selectedTemplate'];coinc=json.loads((t/'coincidences.json').read_text());assert coinc==report['coincidence']
 for detector in ['H1','L1']:
  record=next(f for f in m['files'] if f['detector']==detector);path=t/record['filename'];assert path.stat().st_size==record['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
  with h5py.File(path) as f:raw=f['strain/Strain'][:];epoch=float(f['meta/GPSstart'][()]);assert len(raw)==16777216 and np.isfinite(raw).all()
  data=np.load(t/(detector+'-condition.npz'));meta=json.loads((t/(detector+'-condition.json')).read_text());assert meta['rawSamples']==len(raw) and meta['samples']==4092*1024 and meta['durationSeconds']==4092
  actual=resample_to_delta_t(highpass(TimeSeries(raw,delta_t=1/4096,epoch=epoch),15),1/1024).crop(2,2);assert np.allclose(actual.numpy(),data['strain'],rtol=1e-10,atol=1e-30)
  psd=welch(actual,seg_len=4096,seg_stride=2048,avg_method='median');psd=inverse_spectrum_truncation(interpolate(psd,1/actual.duration),max_filter_len=4096,low_frequency_cutoff=20,trunc_method='hann');assert np.allclose(psd.numpy(),data['psd'],rtol=1e-9,equal_nan=True)
  hp,_=get_fd_waveform(approximant=profile['approximant'],mass1=selected['mass1'],mass2=selected['mass2'],spin1z=0,spin2z=0,f_lower=20,f_final=300,delta_f=psd.delta_f);hp.resize(len(psd));assert hashlib.sha256(hp.numpy().tobytes()).hexdigest()==selected['waveformSHA256']
  follow=np.load(t/(detector+'-followup.npz'));snr=matched_filter(hp,actual,psd=psd,low_frequency_cutoff=20,high_frequency_cutoff=300);assert np.allclose(snr.numpy(),follow['snr'],rtol=1e-8,atol=1e-8)
  # Independent frequency-domain inner product checks the actual normalization at the observed peak.
  values=np.abs(follow['snr']);indices=np.arange(8192,len(actual)-8192);peak=int(indices[np.argmax(values[indices])]);kmin=int(20/psd.delta_f);kmax=int(300/psd.delta_f);ks=np.arange(kmin,kmax);spectrum=np.fft.rfft(actual.numpy())/1024
  norm=np.sqrt(4*psd.delta_f*np.sum(np.abs(hp.numpy()[ks])**2/psd.numpy()[ks]));direct=4*psd.delta_f*np.sum(np.conj(hp.numpy()[ks])*spectrum[ks]/psd.numpy()[ks]*np.exp(2j*np.pi*ks*peak/len(actual)))/norm
  assert np.isclose(abs(direct),values[peak],rtol=1e-6,atol=1e-6)
  triggers=json.loads((t/(detector+'-triggers.json')).read_text());assert triggers['templates']==66 and len(triggers['templatePeaks'])==66
  assert {r['template'] for r in triggers['templatePeaks']}==set(range(66))
  for row in triggers['triggers']:assert 0<=row['template']<66 and np.isfinite(row['snr']) and row['snr']>=profile['threshold']
 for row in coinc['zeroLagUnclustered']:
  assert abs(row['H1GPS']-row['L1GPS'])<=.0150001 and np.isclose(row['networkSNR'],np.hypot(row['H1SNR'],row['L1SNR']))
 assert len(coinc['timeSlides'])==len(profile['timeSlidesSeconds'])
 for original,published in [('detector-analysis.png','published-detector-analysis.png'),('coincidence-analysis.png','published-coincidence-analysis.png')]:
  assert (t/original).read_bytes()==(out/published).read_bytes()
  with Image.open(out/published) as image:assert image.width>=1500 and image.height>=750;image.verify()
print(json.dumps({'status':'success','rawObservedSamples':33554432,'physicalTemplates':66,'independentMatchedFilterNormalizationChecked':True,'zeroLagClusteredCoincidences':len(coinc['zeroLagClustered']),'realFigures':2}))
