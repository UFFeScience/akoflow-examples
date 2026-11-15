# Variant Calling - E. coli Genome Comparison

Adapt the complete scientific chain from the [Pegasus Variant Calling workflow](https://github.com/pegasus-isi/variant-calling-pegasus-workflow) to fourteen real Akoflow activities: reference indexing, six processing activities for each of the two original `tests/2` samples, and a final result/visualization activity.

## Inputs and scientific processing

The complete public observations are **SRR2584866** and **SRR2589044** against the original **E. coli REL606** reference. Four frozen ENA FASTQ gzip files contain 897,543,749 compressed bytes. Preparation verifies the recorded byte counts and MD5 digests; it does not subsample or synthesize reads. Reference SHA-256 and the exact upstream revision are included in `data/input-verification.json` and `data/upstream.json`.

The image is based on the original upstream container pinned by digest and preserves **BWA 0.7.17-r1188, samtools 1.15.1, bcftools 1.15.1 and HTSlib 1.15.1**. The original BWA `mem -t 6`, BAM conversion/sort/index, `bcftools mpileup`, haploid multiallelic variant calls and `vcfutils.pl varFilter` computations are retained. Acquisition uses complete ENA mirrors instead of online fasterq-dump. Local file handoffs replace Pegasus/HTCondor/OSN staging. Reference faidx indexing is prepared upfront; text VCF outputs use the explicit `.vcf` suffix.

## Run

With Go, Python 3 and an amd64 Docker-capable Linux host, run from this directory:

```sh
./prepare.sh
./run.sh
```

Allow 16 GiB RAM and 40 GiB free disk as an initial capacity recommendation rather than a measured minimum. Two concurrent jobs are used. The original six-thread BWA setting can oversubscribe an eight-logical-CPU host; execution measurements therefore describe this declared shared-host profile, not a dedicated benchmark. Preparation requires network access to fetch the frozen observations and image; scientific activities execute offline. No upstream telemetry or email notifications are enabled.

After preparation, the same fourteen-activity DAG can be submitted through the daemon:

```sh
go run ../../tools/daemon-local -root ../.. -example scientific-workflows/variant-calling -lanes 2 -wait=false
```

Use the existing daemon URL and protected env file as documented by your deployment. Inspect the actual run in Desktop before publishing. Manual-plan predictions are placeholders, not measured timing estimates.

## Validation and visual result

The final activity generates `variant-summary.svg`, showing the actual per-sample filtered-variant counts and genomic positions/QUAL values. It also owns `variant-results.tar.gz`, `variant-summary.json` and `variant-positions.tsv`, preserving final bytes after intermediate cleanup. The archive includes both real sorted BAM/BAI files, VCFs and QC reports.

The validator checks complete paired-read accounting, nonzero mapped coverage, BAM integrity and BAI access, real VCF record counts, every VCF REF allele against the frozen reference, archive SHA-256 digests and XML validity of the scientific SVG. Zero variants is permitted as a biological result when input processing and coverage are valid; no positive calls are fabricated. CI validates the exact image/toolchain and full DAG contract; native execution evidence must separately demonstrate the full real computation before publication.

## Provenance

Original source revision `d8fdae78e564ee8eed98515ba86886d0c944e029`, with its Apache-2.0 license and original generator/wrappers in `scripts/upstream/`. The upstream generator is retained for comparison, not executed with its unrelated telemetry hooks. Input manifests and explicit adaptation details are bundled. The completed native run and independent scientific validation are recorded in `evidence/daemon-run.json` and `evidence/scientific-validation.json`.

## Verified production publication

[Open Variant Calling on the production Hub](https://hub.akoflow.com/o/akoflow/scientific-workflows-variant-calling). The measured Linux amd64 Docker execution completed **14/14 activities** in **1673.441 seconds**, including observed file staging. It processed **3,875,488 complete read pairs** and produced **790** and **11** filtered variant records for SRR2584866 and SRR2589044 respectively. Calls are relative to the frozen reference and are not experimentally established biological truth.

![Actual filtered variants and genomic positions](https://hub.akoflow.com/showcase-results/scientific/variant-calling/variant-summary.svg)

The identical executed image is publicly available without a rebuild at:

```text
hub.akoflow.com/akoflow-examples/variant-calling@sha256:4733fd62b59887b9c0cf4445f69b9ebe792a1c8c88d5ca91607446aa83513001
```

[Download validated BAM/BAI, VCF, QC and visual outputs](https://hub.akoflow.com/showcase-results/scientific/variant-calling/variant-results.tar.gz). Native capture, public full-file hashes, source archive layout and rendered-browser evidence passed acceptance; see `evidence/production-acceptance.json`. The original local image identifier is retained in the measured capture and has the same digest as the public alias.
