def dataset(rows=None):
    rows = INPUT['rows'] if rows is None else rows
    require(len(rows) >= 8 and all(len(row) == 2 and all(math.isfinite(v) for v in row) for row in rows), 'invalid regression dataset')
    return {'training': rows[::2], 'validation': rows[1::2]}


def mlflow_training():
    if STAGE == 'ingest-data':
        return {'rows': INPUT['rows'], 'source': 'versioned local regression measurements'}
    if STAGE == 'validate':
        split = dataset(previous()['rows'])
        require(len(split['validation']) > 2, 'insufficient held-out data')
        return split
    if STAGE == 'train':
        split = previous()
        model = regression(split['training'])
        write_pickle('model.pkl', model)
        return {**split, 'model': model}
    if STAGE == 'evaluate':
        result = previous()
        metrics = {'rmse': rmse(result['model'], result['validation']), 'heldOutSamples': len(result['validation'])}
        require(metrics['rmse'] < INPUT['maxRmse'], 'trained model failed held-out evaluation')
        write_json('metrics.json', metrics)
        report('report.html', 'Held-out regression evaluation', metrics)
        return {**result, 'metrics': metrics}
    if STAGE == 'register-model':
        result = previous()
        digest = hashlib.sha256((OUT / 'model.pkl').read_bytes()).hexdigest()
        entry = {'model': 'local-linear-regression', 'version': digest, 'artifact': 'model.pkl', 'metrics': result['metrics']}
        write_json('registry.json', entry)
        return entry
    if STAGE == 'log-mlflow-run':
        os.environ.setdefault('MLFLOW_DISABLE_AGENT_HINT', '1')
        import mlflow
        # Explicit local tracking store: the smoke run never sends data to a remote service.
        tracking = 'sqlite:///' + str((OUT / 'mlflow.db').resolve())
        mlflow.set_tracking_uri(tracking)
        experiment_id = mlflow.create_experiment('akoflow-local-training', artifact_location=(OUT / 'mlflow-artifacts').resolve().as_uri())
        mlflow.set_experiment(experiment_id=experiment_id)
        result = previous()
        with mlflow.start_run(run_name='cpu-smoke') as run:
            mlflow.log_params({'algorithm': 'ordinary-least-squares', 'training_samples': len(result['training'])})
            mlflow.log_metrics({'rmse': result['metrics']['rmse']})
            mlflow.log_artifact(str(OUT / 'model.pkl'))
            run_id = run.info.run_id
        observed = mlflow.tracking.MlflowClient().get_run(run_id)
        require(abs(observed.data.metrics['rmse'] - result['metrics']['rmse']) < 1e-12, 'MLflow did not persist the metric')
        metadata = {'runId': run_id, 'trackingStore': 'mlflow.db', 'status': observed.info.status, 'metrics': observed.data.metrics}
        write_json('mlflow-run.json', metadata)
        return metadata
    raise ValueError(STAGE)


def compute():
    return mlflow_training()
