def dataset(rows=None):
    rows = INPUT['rows'] if rows is None else rows
    require(len(rows) >= 8 and all(len(row) == 2 and all(math.isfinite(v) for v in row) for row in rows), 'invalid regression dataset')
    return {'training': rows[::2], 'validation': rows[1::2]}


def gradient_fit(rows, rate, epochs):
    model = {'weight': 0.0, 'bias': 0.0}
    for _ in range(epochs):
        residuals = [(x, predict(model,x)-y) for x,y in rows]
        model['weight'] -= rate * 2 * statistics.mean(x*error for x,error in residuals)
        model['bias'] -= rate * 2 * statistics.mean(error for _,error in residuals)
    return model


def model_comparison():
    if STAGE == 'freeze-evaluation-set':
        return dataset()
    if STAGE in ('evaluate-a','evaluate-b','evaluate-c'):
        data = previous()
        if STAGE == 'evaluate-a':
            model = regression(data['training'])
        elif STAGE == 'evaluate-b':
            model = {'weight':0., 'bias':statistics.mean(y for _,y in data['training'])}
        else:
            model = gradient_fit(data['training'],0.03,20)
        return {'candidate': STAGE, 'rmse': rmse(model,data['validation']), 'model': model}
    if STAGE == 'compare-metrics':
        rows = sorted([read_stage(p) for p in CONFIG['dependencies'][STAGE]],key=lambda row:row['rmse'])
        write_csv('comparison.csv',[{'candidate':row['candidate'],'rmse':row['rmse']} for row in rows])
        return {'candidates': rows, 'best': rows[0]}
    if STAGE == 'approve-candidate':
        data = previous()
        require(data['best']['rmse'] < INPUT['maxRmse'], 'candidate approval rejected by error threshold')
        report('report.html','Model comparison on held-out data',data)
        return {'approved': data['best']}
    raise ValueError(STAGE)


def compute():
    return model_comparison()
