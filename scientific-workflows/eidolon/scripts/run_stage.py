from common import *
import subprocess

stage, out = arguments()
NAMES=['climate','bioenergy','emissions']
def rscript(code, cwd):
    subprocess.run(['Rscript','--vanilla','-e',code],cwd=cwd,check=True)

if stage=='validate-inputs':
    receipt=inputs()
    write(out/'inputs-validated.json',{'files':len(receipt['files'])})
elif stage.startswith('etl-'):
    name=stage[4:];work=out/('project-'+name)
    shutil.copytree(DATA/'inputs/etl'/name,work/'etl'/name)
    script=work/'etl'/name/('01-extract_transform_load-'+name+'.R')
    subprocess.run(['Rscript','--vanilla',str(script)],cwd=script.parent,check=True)
    shutil.copyfile(work/'tspredit'/(name+'.RData'),out/(name+'.RData'))
elif stage.startswith('mini-'):
    name=stage[5:];work=out/('mini-project-'+name)
    (work/'etl').mkdir(parents=True);(work/'tspredit').mkdir()
    shutil.copyfile(out/(name+'.RData'),work/'tspredit'/(name+'.RData'))
    shutil.copyfile(DATA/'inputs/etl/02-build-minidata.R',work/'etl/02-build-minidata.R')
    subprocess.run(['Rscript','--vanilla','etl/02-build-minidata.R'],cwd=work,check=True)
    code = """
    e <- new.env(); load('tspredit/NAME.RData', envir=e); x <- e[['NAME']]
    ref <- new.env(); load('/app/data/inputs/tspredit/NAME.RData', envir=ref)
    comparison <- all.equal(x,ref[['NAME']],tolerance=1e-10)
    if (!isTRUE(comparison)) stop(paste(comparison, collapse='; '))
    m <- new.env(); load('data/NAME.RData',envir=m); mini <- m[['NAME']]
    stopifnot(length(mini)==1, identical(unname(mini[[1]]),unname(x[[1]])), !is.null(attr(mini,'url')))
    frame <- do.call(rbind,lapply(names(x), function(n) data.frame(series=n,year=names(x[[n]]),value=as.numeric(x[[n]]))))
    write.csv(frame,'../NAME.csv',row.names=FALSE)
    """.replace('NAME',name)
    rscript(code,work)
    df=pd.read_csv(out/(name+'.csv'))
    assert df.series.nunique()>1 and df.value.notna().any()
    write(out/(name+'-validation.json'),{'collection':name,'fullSeries':int(df.series.nunique()),'observations':len(df),'referenceAgreement':True,'miniSeries':1,'completeBytes':(work/'tspredit'/(name+'.RData')).stat().st_size,'miniBytes':(work/'data'/(name+'.RData')).stat().st_size})
else:
    rows=[json.loads((out/(n+'-validation.json')).read_text()) for n in NAMES]
    fig,axes=plt.subplots(3,1,figsize=(11,11),constrained_layout=True)
    labels={'climate':'Annual temperature change (°C)','bioenergy':'Original FAOSTAT energy units','emissions':'Original FAOSTAT emissions units'}
    for ax,name in zip(axes,NAMES):
        df=pd.read_csv(out/(name+'.csv'))
        for series,g in df.groupby('series',sort=False):
            ax.plot(g.year,g.value,label=series,lw=1)
        ax.set_title(name+' — freshly computed original ETL output');ax.set_ylabel(labels[name]);ax.legend(fontsize=5,ncol=3)
    fig.savefig(out/'collections.png');plt.close(fig)
    summary=pd.DataFrame(rows);summary.to_csv(out/'summary.csv',index=False)
    fig,ax=plt.subplots(figsize=(8,4),constrained_layout=True)
    summary.set_index('collection')[['completeBytes','miniBytes']].plot.bar(ax=ax,rot=0)
    ax.set_ylabel('Serialized bytes');ax.set_title('Original Eidolon full objects versus local miniatures')
    fig.savefig(out/'miniature-comparison.png');plt.close(fig)
    assert all(r['referenceAgreement'] and r['miniSeries']==1 for r in rows)
    import zipfile
    with zipfile.ZipFile(out/'computed-collections.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for n in NAMES:archive.write(out/(n+'.csv'),n+'.csv')
    finish(out,['collections.png','miniature-comparison.png','summary.csv','computed-collections.zip'],{'collections':rows,'originalRCodeExecuted':True,'allFullObjectsMatchPinnedPublishedReferences':True})
