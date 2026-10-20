def write_wav(path, samples, rate):
    with wave.open(str(path),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate)
        audio.writeframes(struct.pack('<'+'h'*len(samples),*samples))


def read_wav(path):
    with wave.open(str(path),'rb') as audio:
        require(audio.getnchannels()==1 and audio.getsampwidth()==2,'expected mono PCM16 audio')
        raw=audio.readframes(audio.getnframes())
        return list(struct.unpack('<'+'h'*(len(raw)//2),raw)),audio.getframerate()


def audio_transcription():
    if STAGE == 'ingest-audio':
        rate=INPUT['sampleRate'];count=int(rate*INPUT['tokenSeconds']);samples=[]
        for token in INPUT['tokens']:
            frequency=INPUT['codebook'][token]
            samples.extend(round(14000*math.sin(2*math.pi*frequency*i/rate)) for i in range(count))
        write_wav(OUT/'input.wav',samples,rate)
        return {'audio':'input.wav','samples':len(samples),'rate':rate,'samplesPerToken':count,'recognizer':'bundled synthetic tone vocabulary; not natural speech'}
    if STAGE == 'segment':
        metadata=previous();samples,rate=read_wav(OUT/metadata['audio'])
        midpoint=(len(INPUT['tokens'])//2)*metadata['samplesPerToken']
        write_wav(OUT/'segment-1.wav',samples[:midpoint],rate)
        write_wav(OUT/'segment-n.wav',samples[midpoint:],rate)
        return {'segments':['segment-1.wav','segment-n.wav'],'samplesPerToken':metadata['samplesPerToken'],'rate':rate}
    if STAGE in ('segment-1','segment-n'):
        metadata=previous();samples,rate=read_wav(OUT/(STAGE+'.wav'));size=metadata['samplesPerToken'];tokens=[]
        for offset in range(0,len(samples),size):
            block=samples[offset:offset+size]
            def power(frequency):
                real=sum(sample*math.cos(2*math.pi*frequency*i/rate) for i,sample in enumerate(block))
                imag=sum(sample*math.sin(2*math.pi*frequency*i/rate) for i,sample in enumerate(block))
                return real*real+imag*imag
            measured={token:power(frequency) for token,frequency in INPUT['codebook'].items()}
            tokens.append(max(measured,key=measured.get))
        return {'tokens':tokens,'transcript':' '.join(tokens),'audio':STAGE+'.wav'}
    if STAGE == 'merge-transcript':return {'tokens':read_stage('segment-1')['tokens']+read_stage('segment-n')['tokens']}
    if STAGE == 'summarize':
        tokens=previous()['tokens'];counts={token:tokens.count(token) for token in sorted(set(tokens))}
        return {'tokens':tokens,'summary':f'The {len(tokens)} decoded tone words cover '+', '.join(f'{word} ({count})' for word,count in counts.items())+'.','counts':counts}
    if STAGE == 'publish':
        data=previous();require(data['tokens']==INPUT['tokens'],'audio decoder disagrees with the source vocabulary')
        (OUT/'transcript.txt').write_text(' '.join(data['tokens'])+'\n');(OUT/'summary.md').write_text('# Synthetic tone transcript summary\n\n'+data['summary']+'\n')
        return {'decodedTokens':len(data['tokens']),'exactMatch':True,'counts':data['counts']}
    raise ValueError(STAGE)


def compute():
    return audio_transcription()
