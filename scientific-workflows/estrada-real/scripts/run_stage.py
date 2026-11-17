from common import *
import zipfile
import networkx as nx

stage, out = arguments()
with zipfile.ZipFile(DATA / 'inputs/artifacts.zip') as z:
    graph = json.loads(z.read('grafo\\estrada_real_graph_unified.json'))
    notebook = json.loads(z.read('Estrada_real_final.ipynb'))
if stage == 'validate-graph':
    inputs()
    ids = {n['node_id'] for n in graph['nodes']}
    assert len(ids) == 108 and len(graph['edges']) == 226
    assert all(e['source'] in ids and e['target'] in ids and e['distance_km'] > 0 for e in graph['edges'])
    write(out / 'graph.json', graph)
elif stage == 'compare':
    cfg=json.loads((DATA / 'dag.json').read_text())
    frames=[]
    for a in cfg['spec']['activities']:
        if a['name'] not in ['validate-graph','compare']:
            frames.append(pd.read_csv(out / (a['name']+'.csv')))
    df=pd.concat(frames,ignore_index=True)
    assert len(df) == 104004
    keys=['profile','origin','destination']
    pivot=df.pivot(index=keys,columns='algorithm',values='cost')
    assert np.allclose(pivot.ucs,pivot.astar,rtol=0,atol=1e-6)
    divergences=int((pivot.greedy-pivot.ucs>1e-6).sum())
    assert (pivot.greedy>=pivot.ucs-1e-6).all()
    df.to_csv(out/'comparison.csv',index=False)
    summary=df.groupby(['profile','algorithm']).agg(searches=('cost','size'),mean_expanded=('expanded','mean'),mean_cost=('cost','mean')).reset_index()
    summary.to_csv(out/'summary.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(13,5),constrained_layout=True)
    for algo in ['ucs','greedy','astar']:
        s=summary[summary.algorithm==algo]
        axes[0].plot(s.profile,s.mean_expanded,marker='o',label=algo)
    axes[0].set_ylabel('Mean expanded nodes');axes[0].legend();axes[0].set_title('All ordered origin–destination pairs')
    ratios=pivot.greedy/pivot.ucs
    axes[1].hist(ratios,bins=40,color='#486a93');axes[1].set_xlabel('Greedy cost / optimal cost');axes[1].set_ylabel('Pairs × profiles');axes[1].set_title(f'{divergences:,} Greedy divergences; A* = UCS for all pairs')
    fig.savefig(out/'search-comparison.png');plt.close(fig)
    G=nx.DiGraph()
    positions={n['node_id']:(n['lon'],n['lat']) for n in graph['nodes']}
    for e in graph['edges']:G.add_edge(e['source'],e['target'])
    fig,ax=plt.subplots(figsize=(9,10),constrained_layout=True)
    nx.draw_networkx_edges(G,positions,ax=ax,arrows=False,alpha=.4,width=.6)
    nx.draw_networkx_nodes(G,positions,ax=ax,node_size=12,node_color='#253f67')
    ax.set_axis_on();ax.set_xlabel('Longitude');ax.set_ylabel('Latitude');ax.set_title('Estrada Real — original curated graph: 108 nodes / 226 directed edges')
    fig.savefig(out/'graph-map.png');plt.close(fig)
    finish(out,['comparison.csv','summary.csv','search-comparison.png','graph-map.png'],{'nodes':108,'directedEdges':226,'searches':len(df),'greedyDivergences':divergences,'paperGreedyDivergences':3715,'paperCountMatches':divergences==3715,'astarUcsAgreementPairs':len(pivot),'originalNotebookCells':[19,34,36]})
else:
    graph=json.loads((out/'graph.json').read_text())
    env={'graph':graph}
    for index in [19,34,36]:
        exec(compile(''.join(notebook['cells'][index]['source']),'original-notebook-cell-'+str(index),'exec'),env)
    char,algo=stage.rsplit('-',1);char=char.replace('-','_')
    fn=env[{'ucs':'search_ucs','greedy':'search_greedy','astar':'search_astar'}[algo]]
    rows=[];G=env['G']
    for origin in G:
        for destination in G:
            if origin==destination:continue
            r=fn(G,origin,destination,char)
            assert r is not None
            assert r['path'][0]==origin and r['path'][-1]==destination
            independent=sum(env['edge_cost'](G.edges[a,b],char) for a,b in zip(r['path'],r['path'][1:]))
            assert abs(independent-r['cost'])<1e-6
            rows.append({'profile':char,'algorithm':algo,'origin':origin,'destination':destination,'cost':r['cost'],'expanded':r['expanded'],'time_ms':r['time_ms']})
    pd.DataFrame(rows).to_csv(out/(stage+'.csv'),index=False)
