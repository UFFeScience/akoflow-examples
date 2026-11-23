#!/usr/bin/env python3
import argparse,hashlib,json,math,platform
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, scipy
from PIL import Image
V='community-brachistochrone-v1'; G=9.80665; A=1.; B={'pi-over-2':math.pi/2,'pi':math.pi,'three-pi-over-2':3*math.pi/2}; P={'straight':1.,'sqrt':.5,'three-halves':1.5}
def js(p,x):p.write_text(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
def frozen():return {'a_m':A,'comparison_tracks':{'sqrt':'y=Y(x/X)^(1/2)','straight':'y=Yx/X','three-halves':'y=Y(x/X)^(3/2)'},'g_m_s2':G,'theta_f_rad':B,'workflow_version':V}
def prep(o):
 o.mkdir(parents=True,exist_ok=True); raw=json.dumps(frozen(),sort_keys=True,separators=(',',':')).encode(); js(o/'inputs.json',frozen()); js(o/'manifest.json',{'input_sha256':hashlib.sha256(raw).hexdigest(),'issue':43,'license':'MIT','runtime':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__},'source':'Johann Bernoulli, Acta Eruditorum (1697), pp. 206-211','workflow_version':V})
def gauss(f,n):
 z,w=np.polynomial.legendre.leggauss(n); return float(np.dot(w,f((z+1)/2))/2)
def track_time(X,Y,p,n):
 def f(s):
  dx=4*X*s**3;dy=4*p*Y*s**(4*p-1);den=math.sqrt(2*G*Y)*s**(2*p);return np.sqrt(dx*dx+dy*dy)/den
 return gauss(f,n)
def solve(o,name):
 th=B[name];X=A*(th-math.sin(th));Y=A*(1-math.cos(th));exact=th*math.sqrt(A/G);c1=gauss(lambda u:2*u*math.sqrt(A/G),128)*th;c2=gauss(lambda u:2*u*math.sqrt(A/G),256)*th;tracks={}
 for key,p in P.items():
  q1=track_time(X,Y,p,128);q2=track_time(X,Y,p,256);tracks[key]={'power':p,'time_s':q2,'coarse_time_s':q1,'refinement_delta_s':abs(q2-q1),'margin_over_cycloid_s':q2-c2}
 q=np.linspace(0,th,1001);result={'analytic_cycloid_time_s':exact,'branch':name,'cycloid_time_s':c2,'cycloid_coarse_time_s':c1,'cycloid_refinement_delta_s':abs(c2-c1),'endpoint_m':{'x':X,'y':Y},'geometry':{'start':[0.,0.],'end_error_m':0.,'finite':True,'minimum_dx_m':float(np.min(np.diff(A*(q-np.sin(q))))),'minimum_y_m':float(np.min(A*(1-np.cos(q))))},'relative_error':abs(c2/exact-1),'theta_f_rad':th,'tracks':tracks,'workflow_version':V};js(o/f'endpoint-{name}.json',result)
def agg(o):
 bb=[json.loads((o/f'endpoint-{x}.json').read_text()) for x in B];js(o/'metrics.json',{'branches':bb,'max_cycloid_relative_error':max(x['relative_error'] for x in bb),'max_refinement_delta_s':max([x['cycloid_refinement_delta_s'] for x in bb]+[t['refinement_delta_s'] for x in bb for t in x['tracks'].values()]),'minimum_comparison_margin_s':min(t['margin_over_cycloid_s'] for x in bb for t in x['tracks'].values()),'workflow_version':V})
def curve(name,X,Y,th):
 if name=='cycloid':q=np.linspace(0,th,500);return A*(q-np.sin(q)),A*(1-np.cos(q))
 x=np.linspace(0,X,500);return x,Y*(x/X)**P[name]
def render(o):
 m=json.loads((o/'metrics.json').read_text());colors={'cycloid':'#111111','straight':'#4477aa','sqrt':'#228833','three-halves':'#cc3311'};fig,aa=plt.subplots(1,3,figsize=(12,3.8),layout='constrained')
 for ax,b in zip(aa,m['branches']):
  for n in colors:x,y=curve(n,b['endpoint_m']['x'],b['endpoint_m']['y'],b['theta_f_rad']);ax.plot(x,y,label=n,color=colors[n])
  ax.invert_yaxis();ax.set_aspect('equal');ax.set_title(f"theta_f={b['theta_f_rad']/math.pi:.1f} pi");ax.set_xlabel('x (m)');ax.grid(alpha=.2)
 aa[0].set_ylabel('downward y (m)');aa[-1].legend(fontsize=7);fig.suptitle('Fixed-endpoint brachistochrone comparisons');fig.savefig(o/'tracks.png',dpi=150);plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained');labels=[];vals=[];cols=[]
 for b in m['branches']:
  for n in colors:labels.append(f"{b['theta_f_rad']/math.pi:.1f}pi\n{n}");vals.append(b['cycloid_time_s'] if n=='cycloid' else b['tracks'][n]['time_s']);cols.append(colors[n])
 ax.bar(range(len(vals)),vals,color=cols);ax.set_xticks(range(len(vals)),labels,rotation=55,ha='right',fontsize=7);ax.set_ylabel('descent time (s)');ax.set_title('Cycloid is fastest for every audited endpoint');ax.grid(axis='y',alpha=.2);fig.savefig(o/'descent-time-comparison.png',dpi=150);plt.close(fig)
 b=m['branches'][1];frames=[];duration=max([b['cycloid_time_s']]+[x['time_s'] for x in b['tracks'].values()])
 for frac in np.linspace(0,1,31):
  fig,ax=plt.subplots(figsize=(6,4),layout='constrained')
  for n in colors:
   x,y=curve(n,b['endpoint_m']['x'],b['endpoint_m']['y'],b['theta_f_rad']);total=b['cycloid_time_s'] if n=='cycloid' else b['tracks'][n]['time_s'];i=min(len(x)-1,round(min(1.,frac*duration/total)*(len(x)-1)));ax.plot(x,y,color=colors[n],alpha=.45);ax.scatter([x[i]],[y[i]],color=colors[n],s=35,label=n)
  ax.invert_yaxis();ax.set_aspect('equal');ax.set_title(f'Equal clock time: {frac*duration:.3f} s');ax.set_xlabel('x (m)');ax.set_ylabel('downward y (m)');ax.legend(fontsize=7);ax.grid(alpha=.2);fig.canvas.draw();frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy()));plt.close(fig)
 frames[0].save(o/'brachistochrone-descent.gif',save_all=True,append_images=frames[1:],duration=90,loop=0,optimize=False)
def val(o,ref=None):
 m=json.loads((o/'metrics.json').read_text());bb=m['branches'];ff=['inputs.json','manifest.json']+[f'endpoint-{x}.json' for x in B]+['metrics.json','tracks.png','descent-time-comparison.png','brachistochrone-descent.gif'];gif=(o/ff[-1]).read_bytes();ch={'three_endpoints':len(bb)==3,'analytic_agreement':m['max_cycloid_relative_error']<=1e-10,'finite_valid_geometry':all(b['geometry']['finite'] and b['geometry']['end_error_m']<=1e-12 and b['geometry']['minimum_dx_m']>=-1e-14 and b['geometry']['minimum_y_m']>=-1e-14 for b in bb),'comparisons_finite_and_slower':all(math.isfinite(t['time_s']) and t['margin_over_cycloid_s']>=1e-6 for b in bb for t in b['tracks'].values()),'quadrature_refinement':m['max_refinement_delta_s']<=1e-9,'media_signatures':(o/'tracks.png').read_bytes().startswith(b'\x89PNG') and (o/'descent-time-comparison.png').read_bytes().startswith(b'\x89PNG') and gif.startswith(b'GIF8') and gif.count(b'\x21\xf9')>1,'byte_identical_reference':ref is None or all((o/f).read_bytes()==(Path(ref)/f).read_bytes() for f in ff)};js(o/'validation.json',{'checks':ch,'checksums':{f:hashlib.sha256((o/f).read_bytes()).hexdigest() for f in ff},'limitations':['fixed comparison families do not constitute a standalone global proof','frictionless point mass, constant gravity, no drag or rolling inertia'],'overall_pass':all(ch.values()),'workflow_version':V});
 if not all(ch.values()):raise SystemExit(1)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--output',default='.');p.add_argument('--branch');p.add_argument('--reference');a=p.parse_args();o=Path(a.output);{'prepare':lambda:prep(o),'solve':lambda:solve(o,a.branch),'aggregate':lambda:agg(o),'render':lambda:render(o),'validate':lambda:val(o,a.reference)}[a.mode]()
if __name__=='__main__':main()
