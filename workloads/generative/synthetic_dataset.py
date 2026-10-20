def tokenize(text):
    return re.findall(r'[a-z0-9]+', text.lower())


def synthetic_dataset():
    if STAGE == 'define-schema':return {'required':['id','topic','question','answer'],'topics':INPUT['topics'],'minimumAnswerWords':3}
    if STAGE in ('batch-a','batch-b','batch-n'):
        schema=previous();offset={'batch-a':0,'batch-b':1,'batch-n':2}[STAGE]
        records=[]
        for index in range(INPUT['rowsPerBatch']):
            topic=schema['topics'][(index+offset)%len(schema['topics'])]
            records.append({'id':f'{offset}-{index}','topic':topic['name'],'question':f'How does {topic["name"]} work in example {index}?','answer':topic['explanation']})
        records.append({'id':'shared','topic':schema['topics'][0]['name'],'question':'Shared review question','answer':schema['topics'][0]['explanation']})
        records.append({'id':'invalid','topic':'unknown','question':'missing answer'})
        return {'records':records,'generator':'versioned schema templates; no LLM service'}
    if STAGE == 'filter':
        records=[row for parent in CONFIG['dependencies'][STAGE] for row in read_stage(parent)['records']]
        valid=[row for row in records if all(key in row for key in ('id','topic','question','answer')) and len(row['answer'].split())>=3]
        return {'records':valid,'rejected':len(records)-len(valid)}
    if STAGE == 'deduplicate':
        data=previous();unique={}
        for record in data['records']:
            key=' '.join(tokenize(record['question']))
            unique.setdefault(key,record)
        return {'records':list(unique.values()),'duplicatesRemoved':len(data['records'])-len(unique),'rejected':data['rejected']}
    if STAGE == 'quality-review':
        data=previous();topics={r['topic'] for r in data['records']}
        require(topics=={topic['name'] for topic in INPUT['topics']},'dataset topic coverage is incomplete')
        require(data['duplicatesRemoved']>=2 and data['rejected']==3,'deduplication/schema rejection checks failed')
        return {**data,'quality':{'rows':len(data['records']),'topics':len(topics),'duplicatesRemoved':data['duplicatesRemoved'],'schemaRejected':data['rejected']}}
    if STAGE == 'publish':
        data=previous();(OUT/'synthetic-dataset.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in data['records']))
        return write_json('quality-report.json',data['quality'])
    raise ValueError(STAGE)


def compute():
    return synthetic_dataset()
