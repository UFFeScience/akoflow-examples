from common import *
import csv
import datetime
from datetime import datetime
from statistics import median
import glob
import os
import re
import time
import unicodedata
import zipfile

stage,out=arguments()
def original():
    notebook=json.loads((DATA/'inputs/original.ipynb').read_text())
    env=dict(globals())
    for index in [16,20]:exec(compile(''.join(notebook['cells'][index]['source']),'original-notebook-cell-'+str(index),'exec'),env)
    return env
if stage=='validate-inputs':
    receipt=inputs();assert len(receipt['files'])==11
    write(out/'inputs-validated.json',{'station':'A701','years':list(range(2013,2023)),'files':len(receipt['files'])})
elif stage.startswith('ingest-'):
    year=int(stage[7:]);env=original()
    df,meta=env['process_inmet_data'](folder=str(DATA/'inputs/raw'),selected_years=[year],station_codes=['A701'],save_csv=False)
    assert len(df)>=8760 and df.WMO_Code.nunique()==1
    df.to_csv(out/f'raw-{year}.csv',index=False)
elif stage=='clean':
    raw=pd.concat([pd.read_csv(out/f'raw-{y}.csv') for y in range(2013,2023)],ignore_index=True)
    env=original();clean=env['data_cleaning'](raw,verbose=True)
    assert clean.datetime.notna().all() and clean.datetime.nunique()==len(clean)
    assert clean.Precip.notna().all() and (clean.Precip>=0).all()
    assert 0<len(clean)<=len(raw)
    clean.to_csv(out/'cleaned.csv',index=False)
    write(out/'cleaning.json',{'rawRows':len(raw),'cleanedRows':len(clean),'removedRows':len(raw)-len(clean),'station':'A701','start':str(clean.datetime.min()),'end':str(clean.datetime.max()),'originalNotebookCells':[16,20]})
elif stage=='compare':
    findings=json.loads((out/'cleaning.json').read_text())
    findings['variables']={v:json.loads((out/(v+'.json')).read_text()) for v in ['temperature','precipitation','humidity']}
    with zipfile.ZipFile(out/'observations.zip','w',zipfile.ZIP_DEFLATED) as z:z.write(out/'cleaned.csv','cleaned.csv')
    artifacts=['observations.zip']
    for v in ['temperature','precipitation','humidity']:
        shutil.copyfile(out/(v+'.png'),out/('result-'+v+'.png'));artifacts.append('result-'+v+'.png')
    finish(out,artifacts,findings)
else:
    df=pd.read_csv(out/'cleaned.csv',parse_dates=['datetime']).set_index('datetime').sort_index()
    col={'temperature':'Temp','precipitation':'Precip','humidity':'RH'}[stage]
    x=pd.to_numeric(df[col],errors='coerce');assert x.notna().all()
    fig,ax=plt.subplots(figsize=(12,4),constrained_layout=True)
    if stage=='humidity':
        ax.hist(x,bins=40,color='#426c95');ax.set_xlabel('Relative humidity (%)');ax.set_ylabel('Hourly observations')
    else:
        monthly=x.resample('MS').sum(min_count=1) if stage=='precipitation' else x.resample('MS').mean()
        ax.plot(monthly.index,monthly.values,color='#426c95');ax.set_ylabel('Monthly precipitation total (mm)' if stage=='precipitation' else 'Monthly mean temperature (°C)')
    ax.set_title('INMET A701 São Paulo–Mirante, 2013–2022 — '+stage)
    fig.savefig(out/(stage+'.png'));plt.close(fig)
    write(out/(stage+'.json'),{'observations':len(x),'minimum':float(x.min()),'maximum':float(x.max()),'mean':float(x.mean())})
