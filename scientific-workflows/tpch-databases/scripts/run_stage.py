from common import *
import ast
from datetime import datetime
import io
import os
import subprocess
import tempfile
import time

stage,out=arguments()
def expression(filename):
    tree=ast.parse((DATA/'inputs'/filename).read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='query1' for t in node.targets):
            return eval(compile(ast.Expression(node.value),filename,'eval'),{'datetime':datetime})
    raise RuntimeError('Original Q1 not found')
if stage=='generate':
    inputs();work=out/'generated';work.mkdir()
    subprocess.run(['/opt/dbgen/dbgen','-s','0.01','-f','-T','L'],cwd=work,check=True)
    source=work/'lineitem.tbl';count=0
    with source.open() as src,(out/'lineitem.csv').open('w') as dst:
        for line in src:
            parts=line.rstrip('\n').split('|');assert len(parts)==17 and parts[-1]==''
            dst.write('|'.join(parts[:-1])+'\n');count+=1
    assert count>50000
elif stage=='compare':
    cfg=json.loads((DATA/'dag.json').read_text())
    rows=[json.loads((out/(a['name']+'.json')).read_text()) for a in cfg['spec']['activities'] if a['name'] not in ['generate','compare']]
    assert len(rows)==8
    def values(r):return pd.DataFrame(r['groups']).sort_values(['returnflag','linestatus']).reset_index(drop=True)
    aligned=[r for r in rows if r['mode']=='aligned']
    ref=values(aligned[0]);numeric=[c for c in ref if c not in ['returnflag','linestatus']]
    for r in aligned[1:]:
        table=values(r)
        assert table[['returnflag','linestatus']].equals(ref[['returnflag','linestatus']])
        assert np.allclose(table[numeric],ref[numeric],rtol=1e-9,atol=1e-6)
    counts={r['engine']:int(sum(g['count_order'] for g in r['groups'])) for r in rows if r['mode']=='original' and not r['indexed']}
    assert counts['mongo']!=counts['postgres']
    table=pd.DataFrame([{k:v for k,v in r.items() if k!='groups'} for r in rows]);table.to_csv(out/'metrics.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
    for i,engine in enumerate(['postgres','mongo']):
        orig=next(r for r in rows if r['engine']==engine and r['mode']=='original' and not r['indexed'])
        align=next(r for r in rows if r['engine']==engine and r['mode']=='aligned' and not r['indexed'])
        axes[0].bar(np.array([0,1])+i*.35,[orig['matchedRows'],align['matchedRows']],width=.35,label=engine)
    axes[0].set_xticks([.175,1.175],['Original source cutoffs','Aligned cutoff']);axes[0].set_ylabel('Matched line items');axes[0].legend();axes[0].set_title('Q1 source mismatch: Dec 1 versus Sep 2, 1998')
    axes[1].barh(table.stage,table.medianQueryMs,color='#426c95');axes[1].set_xlabel('Observed median query ms (3 warm repetitions)');axes[1].set_title('Concurrent diagnostic timings; not a controlled ranking')
    fig.savefig(out/'database-comparison.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4),constrained_layout=True)
    groups=[g['returnflag']+'/'+g['linestatus'] for g in ref.to_dict('records')]
    ax.bar(groups,ref['sum_disc_price'],color='#426c95');ax.set_ylabel('Discounted revenue');ax.set_title('Aligned Q1 — independently agreeing PostgreSQL / MongoDB aggregates')
    fig.savefig(out/'aligned-aggregates.png');plt.close(fig)
    write(out/'query-results.json',rows)
    finish(out,['metrics.csv','query-results.json','database-comparison.png','aligned-aggregates.png'],{'query':'TPC-H Q1','scaleFactor':0.01,'originalMatchedRows':counts,'originalSourceMismatchObserved':True,'alignedAllNumericAggregatesAgree':True,'isolatedDatabaseRuns':8,'originalSqlCutoff':'1998-09-02','originalMongoCutoff':'1998-12-01'})
else:
    engine,mode,idx=stage.split('-');indexed=idx=='indexed'
    results=[];timings=[];temp=Path(tempfile.mkdtemp(prefix='tpch-'))
    if engine=='postgres':
        prefix=[]
        if os.geteuid()==0:
            import pwd
            u=pwd.getpwnam('postgres');os.chown(temp,u.pw_uid,u.pw_gid);prefix=['runuser','-u','postgres','--']
        def cmd(args,**kwargs):
            p=subprocess.run(prefix+args,text=True,capture_output=True,**kwargs)
            if p.returncode:raise RuntimeError(str(args)+': '+p.stderr)
            return p.stdout
        socket=temp/'socket';socket.mkdir()
        if prefix:os.chown(socket,u.pw_uid,u.pw_gid)
        cmd(['initdb','-D',str(temp/'db'),'-A','trust','-U','postgres','--no-locale'])
        cmd(['pg_ctl','-D',str(temp/'db'),'-l',str(temp/'server.log'),'-o',"-F -k "+str(socket)+" -h ''",'-w','start'])
        def sql(s):return cmd(['psql','-h',str(socket),'-U','postgres','-v','ON_ERROR_STOP=1','-q','-c',s])
        try:
            schema="CREATE TABLE lineitem (l_orderkey integer,l_partkey integer,l_suppkey integer,l_linenumber integer,l_quantity double precision,l_extendedprice double precision,l_discount double precision,l_tax double precision,l_returnflag char(1),l_linestatus char(1),l_shipdate date,l_commitdate date,l_receiptdate date,l_shipinstruct text,l_shipmode text,l_comment text);"
            sql(schema)
            cmd(['psql','-h',str(socket),'-U','postgres','-v','ON_ERROR_STOP=1','-q','-c',"COPY lineitem FROM STDIN WITH (FORMAT csv,DELIMITER '|')"],input=(out/'lineitem.csv').read_text())
            if indexed:sql('CREATE INDEX shipdate_idx ON lineitem(l_shipdate);')
            sql('ANALYZE lineitem;')
            query=expression('AvaliaPostgreSQL.py').strip().rstrip(';')
            sql('COPY ('+query+') TO STDOUT WITH CSV HEADER')
            for _ in range(3):
                t=time.perf_counter();raw=sql('COPY ('+query+') TO STDOUT WITH CSV HEADER');timings.append((time.perf_counter()-t)*1000)
            for r in pd.read_csv(io.StringIO(raw)).to_dict('records'):
                r['returnflag']=r.pop('l_returnflag');r['linestatus']=r.pop('l_linestatus');results.append(r)
        finally:cmd(['pg_ctl','-D',str(temp/'db'),'-m','fast','-w','stop'])
    else:
        from pymongo import MongoClient
        (temp/'db').mkdir()
        subprocess.run(['mongod','--dbpath',str(temp/'db'),'--bind_ip','127.0.0.1','--port','27017','--logpath',str(temp/'server.log'),'--fork'],check=True,capture_output=True)
        client=MongoClient('mongodb://127.0.0.1:27017',serverSelectionTimeoutMS=30000)
        try:
            orders={}
            with (out/'lineitem.csv').open() as stream:
                for line in stream:
                    a=line.rstrip('\n').split('|');key=int(a[0])
                    orders.setdefault(key,{'_id':key,'oOrderkey':key,'lineitems':[]})['lineitems'].append({'lQuantity':float(a[4]),'lExtendedprice':float(a[5]),'lDiscount':float(a[6]),'lTax':float(a[7]),'lReturnflag':a[8],'lLinestatus':a[9],'lShipdate':datetime.fromisoformat(a[10])})
            collection=client.tpch.orders;collection.insert_many(list(orders.values()))
            if indexed:collection.create_index('lineitems.lShipdate')
            pipeline=expression('AvaliaMongoDB.py')
            if mode=='aligned':pipeline[1]['$match']['lineitems.lShipdate']['$lte']=datetime(1998,9,2)
            list(collection.aggregate(pipeline))
            for _ in range(3):
                t=time.perf_counter();raw=list(collection.aggregate(pipeline));timings.append((time.perf_counter()-t)*1000)
            for r in raw:
                group=r.pop('_id');r['returnflag']=group['lReturnflag'];r['linestatus']=group['lLinestatus'];results.append(r)
        finally:
            client.close()
            subprocess.run(['mongod','--dbpath',str(temp/'db'),'--shutdown'],check=True,capture_output=True)
    shutil.rmtree(temp)
    write(out/(stage+'.json'),{'stage':stage,'engine':engine,'mode':mode,'indexed':indexed,'medianQueryMs':float(np.median(timings)),'matchedRows':int(sum(r['count_order'] for r in results)),'groups':results})
