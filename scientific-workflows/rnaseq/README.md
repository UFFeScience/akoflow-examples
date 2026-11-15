# RNA-seq — Transcript Abundance and Quality Control

Run the unmodified nf-core/rnaseq 3.27.0 pipeline (a1fcdddd3b826fe46eb46f0479f2ff8a7815af05, MIT) through AkôFlow, using the official rapid_quant profile. The original source and license are under upstream/. Four outer activities acquire full observations, run the original Nextflow pipeline with its local executor and preinstalled original module environments, calculate scientific figures and retain final derived outputs. Internal Nextflow task counts/times are recorded separately; four outer activities do not mean the nf-core pipeline has only four tasks.

The real single-end yeast library SRR10143877 contains all 1,039,872 reads and 53,033,472 bases, with no read subsampling for quantification. Full Ensembl release 110 S288c R64-1-1 genome, transcriptome and annotations are frozen with all source lengths and SHA256/ENA MD5. This profile performs abundance estimation and QC for one library, not differential expression. Library type U assumes unstranded single-end reads; Salmon uses its default fragment-length prior rather than a length distribution measured from paired reads.

The scientific pipeline uses original FastQC, fastp trimming, reference preparation, Salmon indexing/quantification and MultiQC processes. Alignment-dependent stages are skipped by the official rapid_quant profile. Original modules execute directly inside the immutable Docker image using Nextflow's local executor, without nested Docker. Sixteen original environment recipes and exact resolved package URLs are retained for provenance. Only acquisition needs internet access after the execution image is prepared; Nextflow and nf-schema are preinstalled, institutional remote configs are disabled by upstream offline handling, and scientific input paths are local.

Prepare with ./prepare.sh, check the contract with ./validate.sh -definition, run ./run.sh and validate with ./validate.sh. Native completion must be measured before scientific execution is claimed. Actual transcript abundance and full-library retention figures will be published with the completed run, all original pipeline reports/trace and tool versions.

Sources: https://github.com/nf-core/rnaseq/tree/a1fcdddd3b826fe46eb46f0479f2ff8a7815af05 ; https://www.ncbi.nlm.nih.gov/sra/SRX6871872 ; https://ftp.ensembl.org/pub/release-110/ .

## Verified production publication

[Open RNA-seq on the production Hub](https://hub.akoflow.com/o/akoflow/scientific-workflows-rnaseq). Native execution completed **4/4 outer activities in 229.333 seconds** and **16 inner Nextflow tasks**, with the complete real 1,039,872-read library. Independent numerical/count/hash checks and actual dark-theme figure rendering passed.

![Actual transcript abundances](https://hub.akoflow.com/showcase-results/scientific/rnaseq/published-transcript-abundance.png)

![Full-library read retention and mapping](https://hub.akoflow.com/showcase-results/scientific/rnaseq/published-library-qc.png)

Exact executed image, transferred without rebuilding:

```text
hub.akoflow.com/akoflow-examples/rnaseq@sha256:edb949835c96cf793c9ef21009d583bb7b93cb845df784ac0e5221d1b9b23acb
```

See `evidence/daemon-run.json`, `evidence/scientific-validation.json` and `evidence/production-acceptance.json` for all native execution, scientific checks, public downloads/image pull and visual acceptance. Temporary Nextflow work/cache symlinks are removed only after complete reports and outputs are archived, before regular-artifact handoff.
