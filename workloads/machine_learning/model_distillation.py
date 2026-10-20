def teacher_value(x):return 1/(1+math.exp(-(INPUT['teacherWeight']*x+INPUT['teacherBias'])))


def model_distillation():
    if STAGE == 'load-teacher':return {'weight':INPUT['teacherWeight'],'bias':INPUT['teacherBias'],'kind':'sigmoid'}
    if STAGE == 'soft-labels':
        teacher=previous();return {'teacher':teacher,'rows':[[x,teacher_value(x)] for x in INPUT['inputs']]}
    if STAGE == 'train-student':return {'model':regression(previous()['rows'])}
    if STAGE == 'quality':
        model=previous()['model'];held_out=[-0.95+i*0.1 for i in range(20)]
        error=rmse(model,[(x,teacher_value(x)) for x in held_out])
        require(error<0.04,'distilled student error is too high')
        return {'rmse':error,'heldOutSamples':len(held_out)}
    if STAGE == 'latency':
        model=previous()['model'];samples=INPUT['inputs']
        started=time.perf_counter_ns();checksum=0.
        for _ in range(100):
            for x in samples:checksum+=predict(model,x)
        elapsed=time.perf_counter_ns()-started
        return {'studentNanosecondsPerPrediction':elapsed/(100*len(samples)),'checksum':checksum,'hardware':'local CPU'}
    if STAGE == 'publish':
        model=read_stage('train-student')['model'];write_pickle('student.pkl',model)
        return write_json('distillation-report.json',{'quality':read_stage('quality'),'latency':read_stage('latency')})
    raise ValueError(STAGE)


def compute():
    return model_distillation()
