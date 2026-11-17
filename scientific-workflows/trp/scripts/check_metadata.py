import tarfile
import pandas as pd

with tarfile.open('/outputs/stage-02.tar.gz') as archive:
    cases = pd.read_csv(archive.extractfile('project/data/processed/tcga-brca/cases-metadata.csv'))
    files = pd.read_csv(archive.extractfile('project/data/processed/tcga-brca/files-metadata.csv'))
    assert int((cases['is_case_of_interest'] == 1).sum()) == 488
    assert files.loc[files['is_file_of_interest'] == 1, 'file_id'].nunique() == 1084
print('Verified the original metadata filtering selects 488 cases and 1084 GDC files.')
