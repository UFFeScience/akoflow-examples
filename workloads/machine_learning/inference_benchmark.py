def inference_benchmark():
    if STAGE == 'freeze-inputs':return {'model':regression(INPUT['rows']),'inputs':[i/100 for i in range(INPUT['samples'])]}
    if STAGE in ('cpu','gpu','edge'):
        data=previous();batch={'cpu':1,'gpu':32,'edge':4}[STAGE]
        started=time.perf_counter_ns();checksum=0.
        for _ in range(INPUT['repetitions']):
            for offset in range(0,len(data['inputs']),batch):
                checksum+=sum(predict(data['model'],x) for x in data['inputs'][offset:offset+batch])
        elapsed=time.perf_counter_ns()-started
        return {'target':STAGE,'hardware':'CPU portable profile','batchSize':batch,'elapsedNanoseconds':elapsed,'predictions':len(data['inputs'])*INPUT['repetitions'],'checksum':checksum}
    if STAGE == 'normalize':
        rows=[read_stage(p) for p in CONFIG['dependencies'][STAGE]]
        require(max(r['checksum'] for r in rows)-min(r['checksum'] for r in rows)<1e-5,'benchmark branches disagree on predictions')
        return {'measurements':[{**row,'nanosecondsPerPrediction':row['elapsedNanoseconds']/row['predictions']} for row in rows]}
    if STAGE == 'compare-cost-and-latency':
        rows=previous()['measurements'];write_csv('benchmark.csv',rows)
        report('report.html','Local CPU batching benchmark (GPU and edge are CPU fallback profiles)',rows)
        return {'measurements':rows,'note':'No GPU or remote edge execution is claimed.'}
    raise ValueError(STAGE)


def compute():
    return inference_benchmark()
