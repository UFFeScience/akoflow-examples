def experiment_response(x):
    return INPUT['offset'] - (x - INPUT['optimum']) ** 2


def feedback_loop():
    if STAGE == 'observations':
        xs = INPUT['observations']
        require(len(xs) >= 3, 'at least three observations are required')
        return {'observations': [[x, experiment_response(x)] for x in xs]}
    if STAGE == 'update-model':
        observations = previous()['observations']
        # Quadratic regression y = a*x^2 + b*x + c via Gaussian elimination.
        matrix = [[sum(x ** (i+j) for x, _ in observations) for j in range(3)] + [sum(y*x**i for x,y in observations)] for i in range(3)]
        for pivot in range(3):
            magnitude = matrix[pivot][pivot]
            require(abs(magnitude) > 1e-12, 'singular experiment design')
            matrix[pivot] = [v/magnitude for v in matrix[pivot]]
            for row in range(3):
                if row != pivot:
                    factor = matrix[row][pivot]
                    matrix[row] = [v-factor*p for v,p in zip(matrix[row],matrix[pivot])]
        coefficients = [matrix[i][-1] for i in range(3)]
        require(coefficients[2] < 0, 'feedback model is not concave')
        return {'coefficients': coefficients, 'observations': observations}
    if STAGE == 'propose-experiments':
        model = previous()
        c,b,a = model['coefficients']
        optimum = -b/(2*a)
        return {'proposals': [optimum-0.1, optimum, optimum+0.1], 'model': model}
    if STAGE == 'safety-check':
        batch = previous()
        require(all(INPUT['minimum'] <= x <= INPUT['maximum'] for x in batch['proposals']), 'proposal exceeds the experiment safety envelope')
        return batch
    if STAGE == 'run-experiments':
        batch = previous()
        return {'proposals': batch['proposals'], 'results': [[x,experiment_response(x)] for x in batch['proposals']], 'prior': batch['model']['observations']}
    if STAGE == 'record-observations':
        results = previous()
        best = max(results['results'],key=lambda row:row[1])
        require(abs(best[0]-INPUT['optimum']) < 1e-6, 'feedback failed to recover the optimum')
        write_json('next-batch.json', {'experiments': results['proposals']})
        report_data = {'before': results['prior'], 'after': results['results'], 'best': best, 'improvement': best[1]-max(y for _,y in results['prior'])}
        require(report_data['improvement'] > 0, 'feedback produced no improvement')
        write_json('feedback-report.json', report_data)
        return report_data
    raise ValueError(STAGE)


def compute():
    return feedback_loop()
