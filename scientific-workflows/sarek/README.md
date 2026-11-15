# Sarek — Regional Germline Variant Calling

Run the unmodified nf-core/sarek 3.12.0 pipeline (786a11bb4f989751d1c4bb87908ffc6096635ff3, MIT) through AkôFlow. Four outer native activities acquire real frozen inputs, execute the original Nextflow variant-calling pipeline, calculate scientific views and retain owned final artifacts. Internal Nextflow task counts/timings are kept separately; four outer activities are not a claim that Sarek has only four tasks.

## Real regional execution profile

The profile calls diploid germline variants on GRCh38 chr20:10000001-11000000, starting from 280,468 genuine HG002 Illumina 2x250 alignment records. All alignments overlapping a 1000bp-flanked interval are retained without downsampling. This is a bounded 1Mb call profile, not whole-genome calling or raw-read mapping. The full compatible 3,263,683,042-byte IGSR GRCh38 reference includes all 2,580 alignment contigs with matching lengths (3,366 total reference contigs). Full reference SHA256, original BAM/index URI, ETag/size/date, exact extraction bounds and frozen file hashes are recorded.

The original published alignment has no read groups. Input freezing adds one explicitly documented combined HG002/ILLUMINA read group and coordinate-sorts the region. A canonical digest of every first-eleven-field SAM record verifies that reads, sequences, qualities, alignment coordinates and CIGARs remain unchanged. No lane-level provenance or new recalibration is inferred. The frozen regional BAM and complete compressed reference are public hash-pinned snapshots of the original unrestricted GIAB/IGSR data; input preparation is not included in native variant-calling timing.

The original pipeline runs with --step variant_calling --tools haplotypecaller and the real BED interval. It retains original reference preparation, GATK HaplotypeCaller and QC/reporting. Optional CNN tranche filtering is explicitly disabled with --skip_tools haplotypecaller_filter: this bounded profile supplies no appropriate external known-site calibration set. Outputs are raw unfiltered research calls. No BQSR, whole-genome processing, trained-filter calibration, clinical interpretation or measured accuracy against a truth set is claimed.

## Execution and result views

Use ./prepare.sh, ./validate.sh -definition, ./run.sh and ./validate.sh. The immutable Docker base already supplies Nextflow 25.10.4, nf-schema 2.7.2, nf-core-utils 0.4.0, nf-fgbio 1.0.0, nf-prov 1.7.0, Python plotting and existing tools; original Sarek dependency recipes are added without modifying upstream source. Twenty-four selected original module recipes use eleven pinned preinstalled environment prefixes. Only acquisition needs network after image preparation. The original pipeline uses Nextflow's local executor inside the activity, with no nested Docker privilege. It permits two inner tasks with two CPUs/4GiB each, within the four-CPU/12GiB native allocation.

Scientific figures show observed allele classes/positions/QUAL/read fractions and actual genotype counts. Counts are derived from the original VCF, with independently checked reference alleles, BAM record integrity and completed task trace. All original reports, trace/timeline, package locks, regional BAM, reference crop and result hashes are retained. Disposable Nextflow symlink work/cache directories are removed only after all original outputs are archived, before regular-artifact handoff. A definition check alone is not scientific completion; completed execution evidence is published only after an actual native run and independent validation.

Sources: https://github.com/nf-core/sarek/tree/786a11bb4f989751d1c4bb87908ffc6096635ff3 ; https://registry.opendata.aws/giab/ ; https://github.com/igsr/1000Genomes_data_indexes/blob/master/README_using_1000genomes_cram.md .

## Verified production publication

[Open Sarek on the production Hub](https://hub.akoflow.com/o/akoflow/scientific-workflows-sarek). The native run completed **4/4 outer activities in 265.812 seconds** and **14 inner Nextflow tasks**, with all 280,468 real regional alignment records. It produced **1,757 original raw VCF records**; allele-class counts are per alternate allele and can exceed record counts at multiallelic sites. All VCF reference alleles, original fields, genotype/allele counts, result hashes and dark-theme scientific figures passed independent checks.

![Actual regional variant observations](https://hub.akoflow.com/showcase-results/scientific/sarek/published-regional-variants.png)

![Actual genotype counts](https://hub.akoflow.com/showcase-results/scientific/sarek/published-genotype-observations.png)

Exact executed image, transferred without rebuilding:

```text
hub.akoflow.com/akoflow-examples/sarek@sha256:a64d040a30f543454d1d2d51ce5c77bdb3022b9d4cf0a6e1b474fac07803bb20
```

See `evidence/daemon-run.json`, `evidence/scientific-validation.json` and `evidence/production-acceptance.json` for native capture, numerical/reference checks, all public download hashes, public Docker pull and actual figure rendering.
