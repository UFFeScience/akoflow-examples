# Scientific source and input attribution

The six notebooks, config.py and Python requirement versions in `upstream/` come from LIS-Unicamp/pan-cancer-analysis v0.1.0, commit 914e8f0b60a8ec5c7df2cedf73b482c183b9aa2b:
https://github.com/LIS-Unicamp/pan-cancer-analysis/tree/v0.1.0

Paper: Towards an automated pipeline to model a complex-network-driven analysis of microRNAs in cancer: a TCGA-BRCA case study.
https://doi.org/10.5753/bsb.2025.15126

The scientific notebooks are preserved unchanged. The upstream repository does not contain an explicit code license; this package does not grant additional rights to third-party source or data. Original attribution and notices are retained. The AkôFlow adapter changes orchestration and transport, not the paper's scientific functions or thresholds.

The four frozen raw metadata/supplementary files distributed by that release are identified by original path, byte length and SHA-256 in `data/provenance.json`. Newly acquired observations come from the public GDC API, https://api.gdc.cancer.gov/, and miRWalk, http://mirwalk.umm.uni-heidelberg.de/. The supplementary table's source and third-party terms remain applicable. No author-computed expression, inference or network output is included as an execution input.
