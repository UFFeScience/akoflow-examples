def dataset(rows=None):
    rows = INPUT['rows'] if rows is None else rows
    require(len(rows) >= 8 and all(len(row) == 2 and all(math.isfinite(v) for v in row) for row in rows), 'invalid regression dataset')
    return {'training': rows[::2], 'validation': rows[1::2]}


def model_ensemble():
    if STAGE == 'prepare-input':return dataset()
    if STAGE in ('predict-a','predict-b','predict-c'):
        data=previous();offset={'predict-a':0,'predict-b':1,'predict-c':2}[STAGE]
        training=[row for i,row in enumerate(data['training']) if i%3!=offset]
        model=regression(training)
        return {'model':model,'predictions':[predict(model,x) for x,_ in data['validation']], 'targets':[y for _,y in data['validation']]}
    if STAGE == 'combine':
        branches=[read_stage(p) for p in CONFIG['dependencies'][STAGE]]
        return {'models':[b['model'] for b in branches],'predictions':[statistics.mean(values) for values in zip(*(b['predictions'] for b in branches))],'targets':branches[0]['targets']}
    if STAGE == 'evaluate':
        data=previous();error=math.sqrt(statistics.mean((p-y)**2 for p,y in zip(data['predictions'],data['targets'])))
        require(error<INPUT['maxRmse'],'ensemble failed held-out validation')
        return {**data,'metrics':{'rmse':error,'models':len(data['models'])}}
    if STAGE == 'publish':
        data=previous();write_pickle('ensemble.pkl',{'models':data['models'],'combiner':'mean'});write_json('metrics.json',data['metrics']);return data['metrics']
    raise ValueError(STAGE)


def compute():
    return model_ensemble()
