def assisted_analysis():
    if STAGE == 'prepare-experiment':
        require(INPUT['steps'] >= 10 and INPUT['decay'] > 0, 'invalid decay experiment')
        return {'initial': INPUT['initial'], 'decay': INPUT['decay'], 'step': INPUT['step'], 'steps': INPUT['steps']}
    if STAGE == 'simulation':
        setup = previous()
        # Euler integration of dC/dt = -k C, with a bounded stability step.
        require(0 < setup['decay'] * setup['step'] < 1, 'unstable integration step')
        value = setup['initial']
        samples = []
        for i in range(setup['steps'] + 1):
            samples.append({'time': i * setup['step'], 'concentration': value})
            value -= setup['step'] * setup['decay'] * value
        return {'samples': samples, 'setup': setup}
    if STAGE == 'measurements':
        data = previous()
        for sample in data['samples']:
            sample['analytic'] = data['setup']['initial'] * math.exp(-data['setup']['decay'] * sample['time'])
        return data
    if STAGE == 'statistics':
        data = previous()
        errors = [abs(s['concentration'] - s['analytic']) for s in data['samples']]
        return {'meanAbsoluteError': statistics.mean(errors), 'maxError': max(errors), 'count': len(errors), 'final': data['samples'][-1]}
    if STAGE == 'ai-interpretation':
        data = previous()
        # Fit the log-linear decay model from observations, independently from statistics.
        rows = [(s['time'], math.log(s['concentration'])) for s in data['samples']]
        model = regression(rows)
        rate = -model['weight']
        interpretation = f'Observed decay rate {rate:.6f}; concentration decreases with time. The fitted half-life is {math.log(2) / rate:.4f} time units.'
        return {'fittedDecayRate': rate, 'halfLife': math.log(2) / rate, 'method': 'log-linear regression', 'interpretation': interpretation}
    if STAGE == 'validate':
        measured = read_stage('statistics')
        inferred = read_stage('ai-interpretation')
        require(measured['maxError'] < INPUT['maxError'], 'numerical integration exceeded error budget')
        require(abs(inferred['fittedDecayRate'] - INPUT['decay']) < 0.02, 'inferred decay rate is inconsistent')
        return {'statistics': measured, 'inference': inferred, 'checksPassed': 2}
    if STAGE == 'report':
        result = previous()
        write_json('analysis.json', result)
        (OUT / 'interpretation.md').write_text('# Decay experiment\n\n' + result['inference']['interpretation'] + '\n')
        return result
    raise ValueError(STAGE)


def compute():
    return assisted_analysis()
