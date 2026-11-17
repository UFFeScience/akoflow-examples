from common import *
from scipy import stats
import os
import zipfile

stage,out=arguments()
classes=json.loads((DATA/'sources.json').read_text())['classes']
notebook=json.loads((DATA/'inputs/original.ipynb').read_text())
if stage=='validate-inputs':
    receipt=inputs();assert len(receipt['files'])==31
    write(out/'inputs-validated.json',{'recordings':30,'classes':6})
elif stage.startswith('features-'):
    label=int(stage[-1]);name=classes[label]
    env=dict(globals(),SAMPLE_RATE=50000,WINDOW_SIZE=2048,HOP_SIZE=1024,MAX_WINDOWS_PER_FILE=50,COL_NAMES=['tach','ub_rad','ub_ax','ub_tan','ob_rad','ob_ax','ob_tan','mic'],ACCEL_COLS=['ub_rad','ub_ax','ub_tan','ob_rad','ob_ax','ob_tan'])
    for i in [6,7]:exec(compile(''.join(notebook['cells'][i]['source']),'original-notebook-cell-'+str(i),'exec'),env)
    rows=[]
    for p in sorted((DATA/'inputs/recordings'/name).rglob('*.csv')):
        values=env['process_file'](str(p),label,name)
        assert len(values)==50
        for v in values:v['file']=str(p.relative_to(DATA/'inputs/recordings'))
        rows.extend(values)
    assert len(rows)==250
    pd.DataFrame(rows).to_csv(out/(stage+'.csv'),index=False)
elif stage=='merge-features':
    df=pd.concat([pd.read_csv(out/f'features-{i}.csv') for i in range(6)],ignore_index=True)
    cols=[c for c in df.columns if c not in ['label','condition','file']]
    assert len(df)==1500 and len(cols)==132 and df.file.nunique()==30
    assert np.isfinite(df[cols].to_numpy()).all()
    df.to_csv(out/'features.csv',index=False)
elif stage.startswith('train-'):
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import f1_score,confusion_matrix
    from sklearn.ensemble import RandomForestClassifier
    import joblib
    model_name=stage[6:];df=pd.read_csv(out/'features.csv');cols=[c for c in df if c not in ['label','condition','file']]
    X=df[cols].to_numpy(dtype=np.float32);y=df.label.to_numpy();groups=df.file.to_numpy()
    cv=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=42)
    if model_name!='rf':
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers
        tf.keras.utils.set_random_seed(42)
        env=dict(keras=keras,layers=layers)
        exec(compile(''.join(notebook['cells'][13]['source']),'original-notebook-cell-13','exec'),env)
    records=[];cm=None
    work=out/(model_name+'-bundle');work.mkdir()
    standard=os.environ.get('AKOFLOW_PROFILE')=='standard'
    epochs=(15 if model_name=='lstm' else 50) if standard else (5 if model_name=='lstm' else 10)
    for fold,(tr,te) in enumerate(cv.split(X,y,groups)):
        assert not set(groups[tr])&set(groups[te])
        sc=StandardScaler();a=sc.fit_transform(X[tr]).astype(np.float32);b=sc.transform(X[te]).astype(np.float32)
        if model_name=='rf':
            model=RandomForestClassifier(n_estimators=200,max_depth=20,min_samples_split=5,min_samples_leaf=2,random_state=42,n_jobs=1)
            model.fit(a,y[tr]);pred=model.predict(b)
        else:
            tf.keras.backend.clear_session();tf.keras.utils.set_random_seed(42+fold)
            model=env['build_'+model_name](132,6)
            if model_name!='mlp':a=a[...,None];b=b[...,None]
            model.fit(a,y[tr],epochs=epochs,batch_size=64,verbose=0)
            pred=model.predict(b,verbose=0).argmax(axis=1)
        records.append({'fold':fold,'f1':float(f1_score(y[te],pred,average='macro')),'testWindows':len(te),'testRecordings':len(set(groups[te]))})
        if fold==4:
            cm=confusion_matrix(y[te],pred,labels=list(range(6))).tolist()
            np.savez_compressed(work/'split.npz',train=a,test=b,train_labels=y[tr],test_labels=y[te])
            if model_name=='rf':joblib.dump(model,work/'model.joblib')
            else:model.save(work/'model.keras')
    result={'model':model_name,'folds':records,'meanF1':float(np.mean([r['f1'] for r in records])),'lastFoldConfusion':cm,'epochs':0 if model_name=='rf' else epochs,'recordingGroupsDisjoint':True}
    write(out/(model_name+'-baseline.json'),result)
    with zipfile.ZipFile(out/(model_name+'-model.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for p in work.iterdir():archive.write(p,p.name)
elif stage=='compare':
    baselines=[json.loads((out/(m+'-baseline.json')).read_text()) for m in ['mlp','cnn','lstm','rf']]
    rows=[json.loads((out/(m+'-'+q+'.json')).read_text()) for m in ['mlp','cnn','lstm'] for q in ['fp32','fp16','int8']]
    assert len(rows)==9 and all(np.isfinite(r['f1']) and 0<=r['f1']<=1 for r in rows)
    assert all(r['calibrationTestOverlap']==0 for r in rows)
    pd.DataFrame(rows).to_csv(out/'metrics.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
    for m in ['mlp','cnn','lstm']:
        s=[r for r in rows if r['model']==m]
        axes[0].plot([r['sizeKiB'] for r in s],[r['f1'] for r in s],marker='o',label=m)
        for r in s:axes[0].annotate(r['quantization'],(r['sizeKiB'],r['f1']),fontsize=7)
    axes[0].set_xscale('log');axes[0].set_ylim(0,1.05);axes[0].set_xlabel('TFLite size (KiB, log scale)');axes[0].set_ylabel('Held-out final-fold macro F1');axes[0].legend()
    axes[1].bar([r['model'] for r in baselines],[r['meanF1'] for r in baselines],color='#426c95');axes[1].set_ylim(0,1.05);axes[1].set_ylabel('Mean macro F1 over five held-out folds')
    fig.suptitle('MAFAULDA — 30 original recordings; portable profile, not paper-score reproduction')
    fig.savefig(out/'quantization-comparison.png');plt.close(fig)
    fig,axes=plt.subplots(1,4,figsize=(14,4),constrained_layout=True)
    for ax,r in zip(axes,baselines):
        ax.imshow(r['lastFoldConfusion'],cmap='Blues');ax.set_title(r['model']);ax.set_xlabel('Predicted fault class');ax.set_ylabel('True fault class')
    fig.savefig(out/'confusion-matrices.png');plt.close(fig)
    with zipfile.ZipFile(out/'quantized-models.zip','w',zipfile.ZIP_DEFLATED) as z:
        for m in ['mlp','cnn','lstm']:
            for q in ['fp32','fp16','int8']:
                p=out/(m+'-'+q+'.tflite');z.write(p,p.name)
    finish(out,['metrics.csv','quantization-comparison.png','confusion-matrices.png','quantized-models.zip'],{'recordings':30,'classes':6,'windows':1500,'features':132,'baselineModels':baselines,'quantizedModels':9,'evaluation':'recording-disjoint 5-fold; quantization calibration=train, evaluation=test','paperScoreAgreementClaimed':False})
else:
    import tensorflow as tf
    from sklearn.metrics import f1_score
    model_name,level=stage.split('-');work=out/(stage+'-bundle');work.mkdir()
    with zipfile.ZipFile(out/(model_name+'-model.zip')) as archive:
        for name in ['model.keras','split.npz']:(work/name).write_bytes(archive.read(name))
    split=np.load(work/'split.npz');model=tf.keras.models.load_model(work/'model.keras')
    converter=tf.lite.TFLiteConverter.from_keras_model(model)
    if level=='fp16':
        converter.optimizations=[tf.lite.Optimize.DEFAULT];converter.target_spec.supported_types=[tf.float16]
    if level=='int8':
        converter.optimizations=[tf.lite.Optimize.DEFAULT]
        a=split['train'];labels=split['train_labels'];rng=np.random.default_rng(42)
        indices=np.concatenate([rng.choice(np.flatnonzero(labels==c),min(100,int((labels==c).sum())),replace=False) for c in range(6)])
        def representative():
            for i in indices:yield [a[i:i+1].astype(np.float32)]
        converter.representative_dataset=representative;converter.target_spec.supported_ops=[tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type=tf.int8;converter.inference_output_type=tf.int8
    b=converter.convert();(out/(stage+'.tflite')).write_bytes(b)
    interpreter=tf.lite.Interpreter(model_content=b,num_threads=1);interpreter.allocate_tensors()
    info=interpreter.get_input_details()[0];output=interpreter.get_output_details()[0];pred=[]
    for row in split['test']:
        x=row[None,...].astype(np.float32)
        if info['dtype']==np.int8:
            scale,z=info['quantization'];assert scale>0
            x=np.clip(np.rint(x/scale+z),-128,127).astype(np.int8)
        interpreter.set_tensor(info['index'],x);interpreter.invoke();pred.append(int(interpreter.get_tensor(output['index']).argmax()))
    write(out/(stage+'.json'),{'model':model_name,'quantization':level,'sizeKiB':len(b)/1024,'f1':float(f1_score(split['test_labels'],pred,average='macro')),'testWindows':len(pred),'calibrationTestOverlap':0})
