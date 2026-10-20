def supervised_tool_loop():
    if STAGE == 'build-context':return {'values':INPUT['values'],'allowedAction':'write-summary-to-outputs'}
    if STAGE == 'propose-action':
        context=previous();return {'action':context['allowedAction'],'file':'tool-result.json','content':{'count':len(context['values']),'sum':sum(context['values']),'mean':statistics.mean(context['values'])}}
    if STAGE == 'policy-check':
        proposal=previous();require(proposal['action']=='write-summary-to-outputs' and proposal['file']=='tool-result.json','tool policy rejected the proposed action')
        return {'proposal':proposal,'policyPassed':True}
    if STAGE == 'human-approval':
        data=previous();approval=INPUT['approval']
        if os.environ.get('AKOFLOW_APPROVAL_FILE'):
            approval=json.loads(Path(os.environ['AKOFLOW_APPROVAL_FILE']).read_text())
        require(approval['decision']=='approve' and approval['scope']==data['proposal']['action'],'the proposed action does not have a matching approval')
        return {**data,'approval':approval,'note':'The default portable run replays a bundled approval fixture; it does not solicit a new human decision.'}
    if STAGE == 'execute-tool':
        data=previous();write_json(data['proposal']['file'],data['proposal']['content'])
        return write_json('execution.json',{'action':data['proposal']['action'],'approval':data['approval'],'output':data['proposal']['file'],'sha256':hashlib.sha256((OUT/data['proposal']['file']).read_bytes()).hexdigest()})
    if STAGE == 'verify':
        execution=previous();actual=json.loads((OUT/execution['output']).read_text())
        require(actual['sum']==sum(INPUT['values']) and actual['count']==len(INPUT['values']),'tool output verification failed')
        require(hashlib.sha256((OUT/execution['output']).read_bytes()).hexdigest()==execution['sha256'],'tool output changed after execution')
        return write_json('verification.json',{'passed':True,'output':actual,'approvalSource':execution['approval']['source']})
    raise ValueError(STAGE)


def compute():
    return supervised_tool_loop()
