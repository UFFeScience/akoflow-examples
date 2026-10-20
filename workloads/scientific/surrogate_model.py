def simulator(x):
    # A damped oscillator response sampled numerically; CPU work, not a timing surrogate.
    total = 0.0
    steps = INPUT.get('integrationSteps', 300)
    for i in range(steps):
        t = (i + 0.5) / steps
        total += math.exp(-x * t) * math.cos(t) / steps
    return total


def interpolate(samples, x):
    pairs = sorted(samples)
    for (x0, y0), (x1, y1) in zip(pairs, pairs[1:]):
        if x0 <= x <= x1:
            ratio = (x - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    raise ValueError('surrogate query outside the sampled interval')


def surrogate_model():
    if STAGE == 'design-samples':
        count = INPUT['samples']
        require(count >= 8, 'surrogate needs at least eight samples')
        xs = [INPUT['minimum'] + (INPUT['maximum'] - INPUT['minimum']) * i / (count - 1) for i in range(count)]
        return {'xs': xs}
    if STAGE in ('simulation-a', 'simulation-n'):
        xs = previous()['xs']
        offset = 0 if STAGE == 'simulation-a' else 1
        return {'samples': [[x, simulator(x)] for x in xs[offset::2]]}
    if STAGE == 'assemble-dataset':
        samples = read_stage('simulation-a')['samples'] + read_stage('simulation-n')['samples']
        samples.sort()
        require(len(samples) == INPUT['samples'], 'simulation shard lost samples')
        return {'samples': samples}
    if STAGE == 'train-surrogate':
        return {'model': {'kind': 'piecewise-linear', 'samples': previous()['samples']}}
    if STAGE == 'validate':
        model = previous()['model']
        queries = [INPUT['minimum'] + (INPUT['maximum'] - INPUT['minimum']) * (i + 0.5) / 19 for i in range(19)]
        errors = [abs(interpolate(model['samples'], x) - simulator(x)) for x in queries]
        validation = {'maxError': max(errors), 'meanError': statistics.mean(errors), 'heldOutSamples': len(queries)}
        require(validation['maxError'] < INPUT['maxError'], 'surrogate failed held-out validation')
        return {'model': model, 'validation': validation}
    if STAGE == 'publish':
        result = previous()
        write_pickle('surrogate.pkl', result['model'])
        write_json('validation.json', result['validation'])
        return {'modelSamples': len(result['model']['samples']), **result['validation']}
    raise ValueError(STAGE)


def compute():
    return surrogate_model()
