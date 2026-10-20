DIGITS={
 '0':['111','101','101','101','111'],'1':['010','110','010','010','111'],
 '2':['111','001','111','100','111'],'3':['111','001','111','001','111'],
 '4':['101','101','111','001','001'],'5':['111','100','111','001','111'],
 '6':['111','100','111','101','111'],'7':['111','001','010','010','010'],
 '8':['111','101','111','101','111'],'9':['111','101','111','001','111'],
}


def document_extraction():
    if STAGE == 'ingest-documents':
        digits=INPUT['invoiceId']+INPUT['amountDigits'];rows=['0'.join(DIGITS[digit][row] for digit in digits) for row in range(5)]
        (OUT/'scan.pbm').write_text('P1\n'+str(len(rows[0]))+' 5\n'+'\n'.join(' '.join(row) for row in rows)+'\n')
        (OUT/'native.txt').write_text(INPUT['nativeText']+'\n')
        return {'scan':'scan.pbm','native':'native.txt','digitCount':len(digits)}
    if STAGE == 'ocr':
        paths=previous();tokens=(OUT/paths['scan']).read_text().split();width,height=int(tokens[1]),int(tokens[2]);pixels=tokens[3:]
        require(height==5 and len(pixels)==width*height,'invalid PBM dimensions')
        decoded=''
        for left in range(0,width,4):
            glyph=[''.join(pixels[row*width+left:row*width+left+3]) for row in range(5)]
            digit=min(DIGITS,key=lambda value:sum(a!=b for expected,actual in zip(DIGITS[value],glyph) for a,b in zip(expected,actual)))
            distance=sum(a!=b for expected,actual in zip(DIGITS[digit],glyph) for a,b in zip(expected,actual))
            require(distance<=1,'OCR glyph exceeds the template tolerance');decoded+=digit
        (OUT/'ocr.txt').write_text(decoded+'\n');return {'digits':decoded,'method':'pixel-template OCR over bundled PBM digits'}
    if STAGE == 'native-text':
        return {'text':(OUT/previous()['native']).read_text().strip()}
    if STAGE == 'classify':
        native=read_stage('native-text')['text'];require('invoice' in native.lower(),'document classifier did not recognize an invoice')
        return {'kind':'invoice','digits':read_stage('ocr')['digits'],'native':native}
    if STAGE == 'extract-fields':
        data=previous();split=len(INPUT['invoiceId']);currency=re.search(r'Currency:\s*([A-Z]{3})',data['native']);customer=re.search(r'Customer:\s*([^;]+)',data['native'])
        require(currency is not None and customer is not None,'missing invoice labels')
        return {'invoiceId':data['digits'][:split],'amount':int(data['digits'][split:]),'currency':currency.group(1),'customer':customer.group(1).strip()}
    if STAGE == 'validate-schema':
        data=previous();require(data['amount']>0 and data['invoiceId'].isdigit(),'invoice schema validation failed')
        require(data['invoiceId']==INPUT['invoiceId'] and data['amount']==int(INPUT['amountDigits']),'OCR extraction disagrees with the source scan')
        return data
    if STAGE == 'publish':return write_json('extraction.json',previous())
    raise ValueError(STAGE)


def compute():
    return document_extraction()
