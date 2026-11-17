from common import *
import os
import subprocess
import tempfile

stage, out = arguments()
if stage == 'validate-inputs':
    inputs()
    df=pd.read_csv(DATA/'inputs/wdbc.data',header=None)
    assert df.shape == (569,32)
    assert set(df[1])=={'M','B'}
    write(out/'inputs-validated.json',{'observations':569,'originalColumns':32})
elif stage == 'compare':
    counts={}
    for name,dims in [('cube-2d',2),('cube-3d',3)]:
        df=pd.read_csv(out/(name+'.csv'))
        columns=['spatial','metric'] if dims==2 else ['spatial','temporal','metric']
        grand=df[df[columns].isna().all(axis=1)]
        assert len(grand)==1 and int(grand.iloc[0]['count'])==569
        assert int(df['count'].sum()) == 569 * (2**dims)
        a=pd.read_csv(out/(name+'-assignments.csv'))
        assert len(a)==569 and a.id.nunique()==569 and a.metric.notna().all()
        counts[name]={'cubeRows':len(df),'assignedObservations':len(a),'metricClusters':int(a.metric.nunique()),'spatialClusters':int(a.spatial.nunique())}
    fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
    a=pd.read_csv(out/'cube-2d-assignments.csv')
    axes[0].scatter(a.radius1,a.texture1,c=a.metric,cmap='turbo',s=13,alpha=.7)
    axes[0].set_xlabel('Mean radius');axes[0].set_ylabel('Mean texture');axes[0].set_title('Original observations; metric-similarity assignments')
    axes[1].scatter(a.x,a.y,c=a.spatial,cmap='tab20',s=22,alpha=.6)
    axes[1].set_xlabel('Illustrative hospital X');axes[1].set_ylabel('Illustrative hospital Y');axes[1].set_title('Authors’ generated spatial dimension; not patient locations')
    fig.suptitle('SQLSIM — original PostgreSQL functions and CUBE queries')
    fig.savefig(out/'similarity-clusters.png');plt.close(fig)
    summary=pd.DataFrame([dict(query=k,**v) for k,v in counts.items()]);summary.to_csv(out/'summary.csv',index=False)
    fig,ax=plt.subplots(figsize=(7,4),constrained_layout=True)
    summary.set_index('query')[['metricClusters','spatialClusters']].plot.bar(ax=ax,rot=0)
    ax.set_ylabel('Measured clusters');ax.set_title('Independent database state per original query')
    fig.savefig(out/'query-comparison.png');plt.close(fig)
    import zipfile
    with zipfile.ZipFile(out/'query-results.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in ['cube-2d.csv','cube-3d.csv','cube-2d-assignments.csv','cube-3d-assignments.csv']:
            archive.write(out/name,name)
    finish(out,['query-results.zip','summary.csv','similarity-clusters.png','query-comparison.png'],{'observations':569,'queries':counts,'databaseIsolation':'one PostgreSQL cluster per activity','seed':0.42})
else:
    temp=Path(tempfile.mkdtemp(prefix='sqlsim-'));cluster=temp/'db';socket=temp/'socket';socket.mkdir()
    prefix=[]
    if os.geteuid()==0:
        import pwd
        u=pwd.getpwnam('postgres')
        os.chown(temp,u.pw_uid,u.pw_gid);os.chown(socket,u.pw_uid,u.pw_gid)
        prefix=['runuser','-u','postgres','--']
    def command(args,**kwargs):
        r=subprocess.run(prefix+args,text=True,capture_output=True,**kwargs)
        if r.returncode: raise RuntimeError(str(args)+': '+r.stderr)
        return r.stdout
    command(['initdb','-D',str(cluster),'-A','trust','-U','postgres','--no-locale'])
    command(['pg_ctl','-D',str(cluster),'-l',str(temp/'server.log'),'-o',"-F -k "+str(socket)+" -h ''",'-w','start'])
    def sql(text):
        return command(['psql','-h',str(socket),'-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1','-q','-c',text])
    try:
        prepare=(DATA/'inputs/data_preparation.sql').read_text().replace('/breastcancer/wdbc.data',str(DATA/'inputs/wdbc.data'))
        sql('SELECT setseed(0.42);'+prepare)
        sql((DATA/'inputs/functions.sql').read_text())
        original=(DATA/'inputs/queries.sql').read_text()
        queries=[q.strip() for q in original.split(';') if 'GROUP BY' in q]
        query=queries[0 if stage=='cube-2d' else 1]
        (out/(stage+'.csv')).write_text(sql('COPY ('+query+') TO STDOUT WITH CSV HEADER'))
        assignments="SELECT b.id,b.diagnosis,b.radius1,b.texture1,ST_X(b.hospital) AS x,ST_Y(b.hospital) AS y,c.centroid AS metric,spatial_sim(b.hospital,"+('3.5' if stage=='cube-2d' else '5')+") AS spatial FROM breastcancer b JOIN cent_assign c ON c.obs_id=b.id ORDER BY b.id"
        (out/(stage+'-assignments.csv')).write_text(sql('COPY ('+assignments+') TO STDOUT WITH CSV HEADER'))
    finally:
        command(['pg_ctl','-D',str(cluster),'-m','fast','-w','stop'])
        shutil.rmtree(temp)
