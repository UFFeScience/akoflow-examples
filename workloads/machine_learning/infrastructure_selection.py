def infrastructure_selection():
    if STAGE == 'profile-workload':
        rows=INPUT['rows'];start=time.perf_counter_ns();model=regression(rows)
        elapsed=max(1,time.perf_counter_ns()-start)
        return {'model':model,'measuredCpuNanoseconds':elapsed,'trainingRows':len(rows)}
    if STAGE in ('local-gpu','hpc','cloud'):
        profile=previous();candidate=INPUT['candidates'][STAGE]
        duration=profile['measuredCpuNanoseconds']/1e9/candidate['assumedSpeedup']+candidate['assumedStartupSeconds']
        return {'candidate':STAGE,'estimatedSeconds':duration,'estimatedCost':duration*candidate['assumedPricePerSecond'],'basis':'declared assumptions and one measured local CPU fit'}
    if STAGE == 'compare-plans':
        candidates=[read_stage(p) for p in CONFIG['dependencies'][STAGE]]
        return {'candidates':sorted(candidates,key=lambda c:(c['estimatedCost'],c['estimatedSeconds']))}
    if STAGE == 'select-scope':
        result=previous();return {'selected':result['candidates'][0],'candidates':result['candidates'],'executionScope':'local CPU smoke profile'}
    if STAGE == 'train':
        decision=previous();model=regression(INPUT['rows']);error=rmse(model,INPUT['rows'])
        require(error<INPUT['maxRmse'],'selected profile training failed')
        write_csv('cost-comparison.csv',decision['candidates'])
        return write_json('decision.json',{**decision,'model':model,'observedRmse':error,'provisionedResources':0})
    raise ValueError(STAGE)


def compute():
    return infrastructure_selection()
