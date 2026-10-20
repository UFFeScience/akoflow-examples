def bounded_agent():
    if STAGE == 'prepare-objective':
        require(INPUT['maxSteps']>=2,'the task requires two bounded tool calls')
        return {'objective':'Summarize the versioned numeric observations.','values':INPUT['values'],'maxSteps':INPUT['maxSteps']}
    if STAGE == 'agent-loop':
        context=previous();trace=[]
        # A finite-state tool agent: actions are selected from a fixed, local allowlist.
        actions=[('measure',lambda: {'count':len(context['values']),'mean':statistics.mean(context['values'])}),('detect-extremes',lambda:{'minimum':min(context['values']),'maximum':max(context['values'])})]
        result={}
        for name,tool in actions:
            require(len(trace)<context['maxSteps'],'agent exceeded its tool budget')
            output=tool();result.update(output);trace.append({'tool':name,'output':output})
        return {'answer':result,'trace':trace,'steps':len(trace),'policy':'fixed local numeric tools; no LLM or arbitrary code execution'}
    if STAGE == 'validate-output':
        data=previous();require(data['answer']['count']==len(INPUT['values']) and abs(data['answer']['mean']-sum(INPUT['values'])/len(INPUT['values']))<1e-12,'agent result did not match the observations')
        write_json('validation.json',{'passed':True,'steps':data['steps'],'maxSteps':INPUT['maxSteps']});return data
    if STAGE == 'publish-result':return write_json('answer.json',previous()['answer'])
    if STAGE == 'store-trace':return write_json('trace.json',{'trace':previous()['trace']})
    raise ValueError(STAGE)


def compute():
    return bounded_agent()
