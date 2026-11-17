import io
import urllib.request
import time

class RemoteZip(io.IOBase):
    def __init__(self, url, length=None, offset=0):
        self.url=url
        self.offset=offset
        if length is None:
            with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=60) as r:
                length=int(r.headers['Content-Length'])
        self.length=length
        self.position=0
    def seekable(self):
        return True
    def seek(self, offset, whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else self.length+offset
        return self.position
    def tell(self):
        return self.position
    def read(self, size=-1):
        if size<0:size=self.length-self.position
        size=min(size,self.length-self.position)
        if size<=0:return b''
        start=self.position+self.offset;end=start+size-1
        for attempt in range(4):
            try:
                req=urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{end}','User-Agent':'Akoflow-scientific-reproduction/1.0'})
                with urllib.request.urlopen(req,timeout=120) as r:
                    if r.status!=206:raise RuntimeError('Server did not honor byte range')
                    if not r.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):
                        raise RuntimeError('Unexpected content range')
                    data=r.read()
                if len(data)!=size:raise RuntimeError('Incomplete byte range')
                self.position+=size
                return data
            except Exception:
                if attempt==3:raise
                time.sleep(2**attempt)
