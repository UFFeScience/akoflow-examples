# SRA Search — crAssphage Reference Screening

Process the complete public **SRR3403832 human gut metagenome**: **1,022,414 read pairs / 2,044,828 mates**. This adaptation of the Pegasus SRA Search workflow builds the upstream crAssphage reference index, stages the full paired observations, aligns them with Bowtie2, sorts/indexes the BAM with samtools, validates the results and generates a measured visual summary.

## Visual result from the measured execution

![Observed SRA Search mapping summary: 2,044,828 processed mates and zero matches to the declared crAssphage reference](https://hub.akoflow.com/showcase-results/scientific/sra-search/mapping-summary.svg)

**Finding: zero reference matches under the declared alignment settings.** Every paired observation was processed; unmapped mates are preserved in the BAM. This is a valid negative search result, not fabricated positive detection and not a general conclusion about other organisms or other references.

## Measured execution

The homeserver AkôFlow daemon completed **5/5 activities in 84.058 seconds**, using two local Docker slots. The native capture retains original execution identifiers, actual timings, attempts, logs and output checksums. Manual-plan predictions are placeholders rather than calibrated benchmark measurements.

ENA byte counts and MD5 digests verified the two full compressed FASTQ files before execution. The paired observations were not subsampled. All five execution activities ran offline; preparation fetched the public data and container dependencies.

## Download and reproduce

- [Complete source bundle, full frozen reads, reference, Dockerfile and shared Go runners](https://hub.akoflow.com/showcase-results/scientific/sra-search/source.tar.gz).
- [Actual sorted BAM, BAI, flagstat, idxstats and processing-summary archive](https://hub.akoflow.com/showcase-results/scientific/sra-search/results.tar.gz).
- [Validation report with processing counts and SHA-256 digests](https://hub.akoflow.com/showcase-results/scientific/sra-search/validation.json).
- [Original vector mapping visualization](https://hub.akoflow.com/showcase-results/scientific/sra-search/mapping-summary.svg).

Extract the source, enter `akoflow-examples/scientific-workflows/sra-search`, and run `./prepare.sh && ./run.sh` with Docker and Go installed. Use the companion environment, scope and topology to run through Desktop. The final stage materializes the archive, report and SVG as owned final outputs so intermediate cleanup does not remove them.

Allow 8 GiB RAM and 5 GiB free disk as an initial capacity recommendation, not a measured minimum. The immutable execution image includes the complete reference and reads:

```text
hub.akoflow.com/akoflow-examples/sra-search@sha256:97cf0b996c5745f39b4c733e84dde417463351d107a81dea93673cd49b7cb35c
```

The public alias distributes the identical image used in the measured run. Its original local tag remains in the historical native execution record; this is one measured execution, not a newly claimed run at the registry address.

## Provenance and adaptation

The source bundle preserves the upstream wrappers, revision and license from [Pegasus SRA Search](https://github.com/pegasus-isi/sra-search-pegasus-workflow). ENA provenance identifies accession SRR3403832 and records download addresses, byte counts and MD5 digests. The upstream crAssphage FASTA is preserved with source metadata. Acquisition uses ENA FASTQ mirrors of the same accession instead of the upstream fasterq-dump downloader.

The declared execution toolchain uses **Bowtie2 2.5.0** and **samtools 1.16.1** from Debian Bookworm. These versions differ from the original upstream container and are explicitly attributed to this adaptation. Negative findings are retained rather than treating the absence of reference matches as proof that the pipeline did not execute.
