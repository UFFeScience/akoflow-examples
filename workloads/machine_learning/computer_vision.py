def computer_vision():
    if STAGE == 'collect-images':
        images=[]
        rng=random.Random(INPUT['seed'])
        for label,pattern in enumerate(INPUT['patterns']):
            for index in range(INPUT['samplesPerClass']):
                pixels=[max(0.,min(1.,value+rng.uniform(-0.15,0.15))) for value in pattern]
                images.append({'pixels':pixels,'label':label,'split':'test' if index%4==0 else 'train'})
        return {'images':images,'shape':INPUT['shape']}
    if STAGE == 'import-labels':
        data=previous()
        require(all(len(item['pixels']) == math.prod(data['shape']) and item['label'] in (0,1) for item in data['images']),'invalid image/label pairing')
        return data
    if STAGE == 'augment':
        data=previous()
        augmented=[{**item,'pixels':[min(1.,v*0.9+0.02) for v in item['pixels']]} for item in data['images'] if item['split']=='train']
        return {**data,'images':data['images']+augmented,'augmentedCount':len(augmented)}
    if STAGE == 'train-detector':
        data=previous()
        prototypes=[]
        for label in (0,1):
            group=[item['pixels'] for item in data['images'] if item['split']=='train' and item['label']==label]
            prototypes.append([statistics.mean(values) for values in zip(*group)])
        return {'model':{'kind':'nearest-centroid-image-classifier','prototypes':prototypes,'shape':data['shape']},'test':[item for item in data['images'] if item['split']=='test']}
    if STAGE == 'evaluate':
        data=previous()
        def classify(pixels):
            return min(range(2),key=lambda label:sum((a-b)**2 for a,b in zip(pixels,data['model']['prototypes'][label])))
        correct=sum(classify(item['pixels'])==item['label'] for item in data['test'])
        metrics={'dataset':'bundled geometric-pattern images (not CIFAR-10)','accuracy':correct/len(data['test']),'testImages':len(data['test'])}
        require(metrics['accuracy']>=0.9,'vision classifier failed held-out validation')
        write_json('vision-metrics.json',metrics)
        return {'model':data['model'],'metrics':metrics}
    if STAGE == 'package-model':
        data=previous();write_pickle('model.pkl',data['model']);return data['metrics']
    raise ValueError(STAGE)


def compute():
    return computer_vision()
