def tokenize(text):
    return re.findall(r'[a-z0-9]+', text.lower())


def vectorize(text, vocabulary, idf):
    tokens=tokenize(text)
    vector=[tokens.count(term)*idf[index] for index,term in enumerate(vocabulary)]
    norm=math.sqrt(sum(value*value for value in vector)) or 1
    return [value/norm for value in vector]


def retrieve(index, question):
    query=vectorize(question,index['vocabulary'],index['idf'])
    scored=[(sum(a*b for a,b in zip(query,chunk['vector'])),chunk) for chunk in index['chunks']]
    score,chunk=max(scored,key=lambda item:item[0])
    return {'score':score,'document':chunk['document'],'text':chunk['text']}


def rag_indexing():
    if STAGE == 'collect-documents':
        require(len(INPUT['documents'])>=3,'index needs at least three documents')
        return {'documents':INPUT['documents']}
    if STAGE == 'clean':
        docs=previous()['documents']
        return {'documents':[{'id':doc['id'],'text':' '.join(re.sub('<[^>]+>',' ',doc['text']).split())} for doc in docs]}
    if STAGE == 'chunk':
        chunks=[]
        for doc in previous()['documents']:
            sentences=re.split(r'(?<=[.!?])\s+',doc['text'])
            chunks.extend({'document':doc['id'],'text':text} for text in sentences if tokenize(text))
        return {'chunks':chunks}
    if STAGE == 'embed':
        chunks=previous()['chunks'];vocabulary=sorted({term for chunk in chunks for term in tokenize(chunk['text'])})
        idf=[math.log((len(chunks)+1)/(1+sum(term in tokenize(c['text']) for c in chunks)))+1 for term in vocabulary]
        return {'vocabulary':vocabulary,'idf':idf,'chunks':[{**c,'vector':vectorize(c['text'],vocabulary,idf)} for c in chunks],'method':'normalized TF-IDF; no hosted embedding API'}
    if STAGE == 'build-index':
        index=previous();write_json('index.json',index);return index
    if STAGE in ('retrieval-tests','answer-tests'):
        index=previous();results=[]
        for question in INPUT['questions']:
            answer=retrieve(index,question['question'])
            passed=(answer['document']==question['document']) if STAGE=='retrieval-tests' else (question['contains'].lower() in answer['text'].lower())
            results.append({'question':question['question'],'answer':answer,'passed':passed})
        require(all(r['passed'] for r in results),f'{STAGE} failed known-answer checks')
        return {'tests':results,'passed':len(results),'total':len(results)}
    if STAGE == 'publish':
        return write_json('evaluation.json',{'retrieval':read_stage('retrieval-tests'),'answers':read_stage('answer-tests'),'answerMethod':'extractive retrieval from indexed source sentences'})
    raise ValueError(STAGE)


def compute():
    return rag_indexing()
