from collections import defaultdict
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from acquisition import digest

GROUPS = ['basal-like', 'her2-enriched', 'luminal-a', 'luminal-b', 'normal']


def validate_project(project, output):
    rows = []
    for group in GROUPS:
        folder = project / 'data/processed/networks' / group
        inferred = pd.read_csv(folder / 'inferred-interactions.csv')
        interactions = pd.read_csv(folder / 'interaction-network-edges.csv')
        nodes = pd.read_csv(folder / 'interaction-network-nodes.csv')
        associations = pd.read_csv(folder / 'association-network-edges.csv')
        all_associations = pd.read_csv(folder / 'inferred-associations.csv')
        assert len(inferred) > 0 and len(interactions) > 0, group
        assert np.isfinite(inferred[['correlation', 'pvalue', 'qvalue']].to_numpy()).all(), group
        assert inferred['correlation'].between(-1, 1).all(), group
        assert inferred['pvalue'].between(0, 1).all() and inferred['qvalue'].between(0, 1).all(), group
        chosen = inferred[(inferred['correlation'] < -0.3) & (inferred['qvalue'] < 0.05)]
        expected = set(zip(chosen['mirna_name'], chosen['gene_name']))
        actual = set(zip(interactions['source'], interactions['target']))
        assert expected == actual, 'Interaction membership differs from unrounded thresholds: ' + group
        assert set(nodes['id']) == set(interactions['source']) | set(interactions['target']), group
        expected_associations = all_associations[all_associations['association'] > 0.1]
        assert set(zip(expected_associations['node_a'], expected_associations['node_b'])) == set(zip(associations['source'], associations['target'])), group
        neighbors = defaultdict(set)
        for source, target in actual:
            neighbors[source].add(target)
        for row in all_associations.itertuples():
            a, b = neighbors[row.node_a], neighbors[row.node_b]
            recomputed = len(a & b) / len(a | b)
            assert abs(recomputed - row.association) < 1e-10, group
        rows.append({'group': group, 'inferredPairs': len(inferred), 'interactionEdges': len(interactions), 'interactionNodes': len(nodes), 'associationEdges': len(associations)})
    provenance = json.loads((project / 'provenance.json').read_text())
    for record in provenance['seedFiles']:
        assert digest(project / record['path']) == record['sha256']
    gdc = [json.loads(p.read_text()) for p in (project / 'receipts/gdc').glob('*.json')]
    mirwalk = [json.loads(p.read_text()) for p in (project / 'receipts/mirwalk').glob('*.json')]
    no_hits = [json.loads(p.read_text()) for p in (project / 'receipts/mirwalk-no-hits').glob('*.json')]
    for record in no_hits:
        page = project / record['responsePath']
        assert record['status'] == 'no-match' and digest(page) == record['sha256']
        assert '<h2>No ID matched your search criteria.</h2>' in page.read_text()
    files = pd.read_csv(project / 'data/processed/tcga-brca/files-metadata.csv')
    expected_files = set(files.loc[files['is_file_of_interest'] == 1, 'file_id'])
    assert {r['file_id'] for r in gdc} == expected_files
    expressed = pd.read_csv(project / 'data/processed/tcga-brca/expressed-mirnas.csv')
    assert {r['accession'] for r in mirwalk + no_hits} == set(expressed.loc[expressed['is_expressed'] == 1, 'accession_id'])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for axis, key, title in [(axes[0], 'interactionEdges', 'Selected miRNA–mRNA interactions'), (axes[1], 'associationEdges', 'miRNA association edges')]:
        axis.bar([r['group'] for r in rows], [r[key] for r in rows], color='#222222')
        axis.set_title(title)
        axis.tick_params(axis='x', rotation=25)
    fig.suptitle('TRP — newly computed TCGA-BRCA networks')
    fig.tight_layout()
    fig.savefig(output / 'network-summary.png', dpi=160)
    plt.close(fig)
    return {'status': 'passed', 'upstreamVersion': provenance['version'], 'upstreamCommit': provenance['commit'], 'rawMetadataMode': provenance['metadataMode'], 'referenceOutputsUsedAsInputs': False, 'groups': rows, 'gdcFileCount': len(gdc), 'gdcBytes': sum(r['bytes'] for r in gdc), 'mirwalkFileCount': len(mirwalk), 'mirwalkNoMatchCount': len(no_hits), 'mirwalkNoMatchAccessions': sorted(r['accession'] for r in no_hits), 'checks': ['Frozen raw input hashes', 'Full selected GDC UUID coverage with vendor MD5 and length', 'Expressed-miRNA coverage for miRWalk downloads', 'Finite Spearman/FDR values and mathematical bounds', 'Unrounded correlation/FDR thresholds agree with network edges', 'Interaction node closure', 'Every Jaccard association independently recomputed', 'Association threshold membership']}
