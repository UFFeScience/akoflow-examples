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


def hyperparameter_search():
    if STAGE == 'prepare-dataset':
        return dataset()
    if STAGE.startswith('trial-'):
        data = previous()
        index = {'trial-1': 0, 'trial-2': 1, 'trial-n': 2}[STAGE]
        candidate = INPUT['trials'][index]
        model = gradient_fit(data['training'], candidate['learningRate'], candidate['epochs'])
        return {'candidate': STAGE, 'model': model, 'rmse': rmse(model,data['validation']), **candidate}
    if STAGE == 'compare-trials':
        trials = [read_stage(name) for name in CONFIG['dependencies'][STAGE]]
        trials.sort(key=lambda trial:trial['rmse'])
        require(trials[0]['rmse'] < INPUT['maxRmse'], 'no hyperparameter candidate reached the error target')
        write_csv('leaderboard.csv', [{k:v for k,v in trial.items() if k != 'model'} for trial in trials])
        return {'trials': trials, 'best': trials[0]}
    if STAGE == 'register-best':
        best = previous()['best']
        write_pickle('best-model.pkl', best['model'])
        return best
    raise ValueError(STAGE)


def compute():
    return hyperparameter_search()
