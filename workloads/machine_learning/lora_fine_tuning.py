def lora_training():
    if STAGE == 'fetch-base-model':
        return {'weights': INPUT['baseWeights'], 'rank': 1, 'source': 'bundled 2x2 base matrix'}
    if STAGE == 'prepare-examples':
        return {**previous(), 'examples': INPUT['examples']}
    if STAGE == 'fine-tune-adapters':
        data = previous()
        base,examples = data['weights'],data['examples']
        a,b = [0.1,-0.05],[0.0,0.0]
        def error(aa,bb):
            return statistics.mean((sum((base[i][j]+bb[i]*aa[j])*x[j] for j in range(2))-target[i])**2 for x,target in examples for i in range(2))
        initial = error(a,b)
        for _ in range(INPUT['epochs']):
            ga,gb = [0.,0.],[0.,0.]
            for x,target in examples:
                projection = sum(a[j]*x[j] for j in range(2))
                for i in range(2):
                    residual = sum(base[i][j]*x[j] for j in range(2)) + b[i]*projection - target[i]
                    gb[i] += residual*projection/len(examples)
                    for j in range(2):
                        ga[j] += residual*b[i]*x[j]/len(examples)
            a = [v-INPUT['learningRate']*g for v,g in zip(a,ga)]
            b = [v-INPUT['learningRate']*g for v,g in zip(b,gb)]
        return {'baseWeights': base, 'adapterA': a, 'adapterB': b, 'initialMse': initial, 'finalMse': error(a,b)}
    if STAGE == 'evaluate':
        trained = previous()
        require(trained['finalMse'] < 0.01 and trained['finalMse'] < trained['initialMse']/10, 'rank-one adapter did not learn the target update')
        write_json('evaluation.json', {'initialMse': trained['initialMse'], 'finalMse': trained['finalMse'], 'rank': 1})
        return trained
    if STAGE == 'publish-adapter':
        result = previous()
        write_pickle('adapter.bin', {'A': result['adapterA'], 'B': result['adapterB'], 'rank': 1})
        return {'rank': 1, 'parameters': 4, 'mse': result['finalMse']}
    if STAGE == 'record-lineage':
        data = previous()
        lineage = {'baseDigest': hashlib.sha256(json.dumps(data['baseWeights']).encode()).hexdigest(), 'datasetDigest': hashlib.sha256(json.dumps(INPUT['examples']).encode()).hexdigest(), 'method': 'rank-one additive adapter with gradient descent'}
        write_json('lineage.json', lineage)
        return lineage
    raise ValueError(STAGE)


def compute():
    return lora_training()
