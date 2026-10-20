def anomaly_detection():
    if STAGE == 'collect-signals':
        require(len(INPUT['normal'])>=10,'insufficient calibration signals')
        return {'normal':INPUT['normal'],'validation':INPUT['validation']}
    if STAGE == 'build-features':
        data=previous()
        # Remove the declared sensor offset before calibrating the Gaussian model.
        offset=INPUT['nominal']
        return {'normal':[value-offset for value in data['normal']], 'validation':[[value-offset,label] for value,label in data['validation']], 'feature':'deviation from nominal sensor amplitude', 'nominal':offset}
    if STAGE == 'train-detector':
        data=previous()
        mean,std=statistics.mean(data['normal']),statistics.stdev(data['normal'])
        require(std>0,'zero sensor variance')
        return {'model':{'mean':mean,'std':std},'validation':data['validation']}
    if STAGE == 'score-validation':
        data=previous();model=data['model']
        return {'model':model,'scored':[{'value':value+INPUT['nominal'],'label':label,'score':abs(value-model['mean'])/model['std']} for value,label in data['validation']]}
    if STAGE == 'choose-threshold':
        data=previous();candidates=[]
        for threshold in INPUT['thresholds']:
            tp=sum(r['score']>=threshold and r['label']==1 for r in data['scored'])
            fp=sum(r['score']>=threshold and r['label']==0 for r in data['scored'])
            fn=sum(r['score']<threshold and r['label']==1 for r in data['scored'])
            candidates.append({'threshold':threshold,'f1':2*tp/max(1,2*tp+fp+fn)})
        best=max(candidates,key=lambda c:c['f1']);require(best['f1']>=0.9,'no anomaly threshold passed validation')
        return {**data,'best':best}
    if STAGE == 'publish':
        data=previous()
        anomalies=[r for r in data['scored'] if r['score']>=data['best']['threshold']]
        write_json('anomalies.json',{'anomalies':anomalies,'threshold':data['best']['threshold']})
        write_json('metrics.json',data['best'])
        return {'detected':len(anomalies),**data['best']}
    raise ValueError(STAGE)


def compute():
    return anomaly_detection()
