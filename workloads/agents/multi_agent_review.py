def multi_agent_review():
    if STAGE == 'shared-context':return {'measurements':INPUT['measurements'],'claimedMean':INPUT['claimedMean'],'tolerance':INPUT['tolerance']}
    if STAGE == 'research':
        data=previous();return {'role':'research','observations':len(data['measurements']),'mean':statistics.mean(data['measurements']),'stdev':statistics.stdev(data['measurements'])}
    if STAGE == 'code':
        data=previous();total=0.
        for value in data['measurements']:total+=value
        return {'role':'code','recomputedMean':total/len(data['measurements']),'allFinite':all(math.isfinite(value) for value in data['measurements'])}
    if STAGE == 'domain':
        data=previous();return {'role':'domain','withinBounds':all(INPUT['minimum']<=value<=INPUT['maximum'] for value in data['measurements']),'claimedMean':data['claimedMean']}
    if STAGE == 'critic-review':
        research,code,domain=(read_stage(name) for name in ('research','code','domain'))
        require(code['allFinite'] and domain['withinBounds'],'parallel reviewers found invalid measurements')
        require(abs(research['mean']-code['recomputedMean'])<INPUT['tolerance'],'independent reviewers disagree')
        claimAccepted=abs(research['mean']-domain['claimedMean'])<INPUT['tolerance']
        return {'research':research,'code':code,'domain':domain,'claimAccepted':claimAccepted,'correctedMean':research['mean']}
    if STAGE == 'synthesize':
        review=previous();text=f'Three independent local reviewers checked {review["research"]["observations"]} measurements. The recomputed mean is {review["correctedMean"]:.6f}. The supplied claim was '+('accepted.' if review['claimAccepted'] else 'rejected and corrected.')
        return {'review':review,'synthesis':text,'agents':'deterministic local reviewer programs; no hosted LLM service'}
    if STAGE == 'publish-evidence':
        data=previous();(OUT/'synthesis.md').write_text('# Parallel review\n\n'+data['synthesis']+'\n');write_json('review.json',data['review']);return {'claimAccepted':data['review']['claimAccepted'],'correctedMean':data['review']['correctedMean']}
    raise ValueError(STAGE)


def compute():
    return multi_agent_review()
