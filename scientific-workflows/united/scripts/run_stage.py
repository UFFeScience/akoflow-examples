from common import *
import pyreadr
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix

stage, out = arguments()
config = json.loads((DATA / 'dag.json').read_text())

def load(name):
    df = next(iter(pyreadr.read_r(str(DATA / 'inputs' / (name + '.RData'))).values()))
    assert {'value', 'event'} <= set(df.columns)
    assert len(df) > 1000 and df['value'].notna().all()
    return df

if stage == 'validate-inputs':
    inputs()
    rows = {p.stem: len(load(p.stem)) for p in sorted((DATA / 'inputs').glob('*.RData'))}
    write(out / 'inputs-validated.json', rows)
elif stage == 'compare':
    results = [json.loads((out / (a['name'] + '.json')).read_text()) for a in config['spec']['activities'] if a['name'] not in ['validate-inputs', 'compare']]
    fig, axes = plt.subplots(4, 1, figsize=(12, 11), constrained_layout=True)
    for ax, name in zip(axes, sorted({r['series'] for r in results})):
        df = load(name)
        ax.plot(df['value'].to_numpy(), lw=.8, color='#27374d')
        mask = df['event'].astype(bool).to_numpy()
        ax.fill_between(np.arange(len(df)), 0, 1, where=mask, transform=ax.get_xaxis_transform(), alpha=.18, color='red', label='Original anomaly labels')
        for r in [v for v in results if v['series'] == name]:
            idx = np.array(r['detected'], dtype=int)
            ax.scatter(idx, df['value'].to_numpy()[idx], s=9, label=r['detector'], alpha=.65)
        ax.set_title(name)
        ax.legend(loc='upper right', fontsize=7)
    fig.suptitle('UniTED / NAB — complete original series and measured detections')
    fig.savefig(out / 'detections.png');plt.close(fig)
    table = pd.DataFrame([{k:v for k,v in r.items() if k != 'detected'} for r in results])
    table.to_csv(out / 'metrics.csv', index=False)
    fig, ax = plt.subplots(figsize=(11, 4), constrained_layout=True)
    for detector in ['arima', 'rolling']:
        sub=table[table.detector==detector]
        ax.plot(sub.series, sub.f1, marker='o', label=detector)
    ax.set_ylim(0, 1.05);ax.set_ylabel('Point-wise test F1');ax.legend();ax.set_title('Held-out evaluation; not the NAB temporal score')
    fig.savefig(out / 'metrics.png');plt.close(fig)
    assert len(results) == 8
    for r in results:
        assert 0 <= r['f1'] <= 1
        assert r['tn'] + r['fp'] + r['fn'] + r['tp'] == r['test_points']
        assert min(r['detected'], default=r['train_points']) >= r['train_points']
    finish(out, ['detections.png','metrics.png','metrics.csv'], {'series':4,'detectorRuns':8,'totalInputPoints':sum(r['points'] for r in results)//2,'evaluation':'held-out point-wise; Python adaptation'})
else:
    detector = stage.rsplit('-',1)[1]
    name = stage.rsplit('-',1)[0].replace('-','_')
    df = load(name);x = df.value.to_numpy(dtype=float);cut = len(x)//4
    if detector == 'arima':
        model = ARIMA(x[:cut], order=(2,0,2)).fit()
        fitted = model.apply(x, refit=False)
        residual = x - fitted.predict()
    else:
        history=pd.Series(x).shift(1)
        baseline=history.rolling(48,min_periods=12).mean()
        residual=x-baseline.to_numpy()
    scale=np.nanstd(residual[12:cut]);center=np.nanmean(residual[12:cut])
    assert np.isfinite(scale) and scale>0
    pred=np.abs(residual-center)>3*scale
    pred[:cut]=False
    labels=df.event.astype(bool).to_numpy()
    precision,recall,f1,_=precision_recall_fscore_support(labels[cut:],pred[cut:],average='binary',zero_division=0)
    tn,fp,fn,tp=confusion_matrix(labels[cut:],pred[cut:],labels=[False,True]).ravel()
    write(out / (stage+'.json'),{'series':name,'detector':detector,'points':len(x),'train_points':cut,'test_points':len(x)-cut,'precision':float(precision),'recall':float(recall),'f1':float(f1),'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp),'detected':np.flatnonzero(pred).tolist()})
