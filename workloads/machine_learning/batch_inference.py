def batch_inference():
    if STAGE == 'load-model':
        return {'model': regression(INPUT['training']), 'inputs': INPUT['inputs']}
    if STAGE == 'partition-input':
        data = previous()
        return {'model': data['model'], 'shards': {name: [[i,x] for i,x in enumerate(data['inputs']) if i % 3 == offset] for offset,name in enumerate(('a','b','n'))}}
    if STAGE.startswith('infer-shard-'):
        data = previous()
        shard = STAGE.rsplit('-',1)[1]
        return {'predictions': [{'index': i, 'input': x, 'prediction': predict(data['model'],x)} for i,x in data['shards'][shard]]}
    if STAGE == 'merge-predictions':
        predictions = [p for parent in CONFIG['dependencies'][STAGE] for p in read_stage(parent)['predictions']]
        predictions.sort(key=lambda p:p['index'])
        require([p['index'] for p in predictions] == list(range(len(INPUT['inputs']))), 'inference shards have gaps or duplicate rows')
        return {'predictions': predictions}
    if STAGE == 'publish':
        predictions = previous()['predictions']
        (OUT / 'predictions.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in predictions))
        return write_json('batch-summary.json', {'rows': len(predictions), 'minimum': min(p['prediction'] for p in predictions), 'maximum': max(p['prediction'] for p in predictions)})
    raise ValueError(STAGE)


def compute():
    return batch_inference()
