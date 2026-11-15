# Further executable scientific workflow candidates

Inspected 2026-11-15. These are source-level findings; none of the following candidates has been executed or adapted here.

| Candidate | Actual data and calculation | Available execution materials | Remaining work |
|---|---|---|---|
| [SRA Search](https://github.com/pegasus-isi/sra-search-pegasus-workflow) | Downloads NCBI SRA reads, builds a Bowtie2 reference index, aligns, sorts/indexes BAM and packages results. | Container definition, generator, wrappers, reference `examples/1/crassphage.fna`, accession list `examples/1/sra_ids.txt` (`SRR3403832`); 1- and 10-input examples. | Validate accession download, pin tools/image, adapt DAG and file transfers. Original tools require outbound IPv4 for SRA downloads; freeze data before offline runs. |
| [Variant Calling](https://github.com/pegasus-isi/variant-calling-pegasus-workflow) | SRA reads against E. coli REL606; BWA alignment, samtools conversion, bcftools variant analysis. | Dockerfile, reference genome, accession lists in `tests/2/sra_ids.txt` (`SRR2584866`, `SRR2589044`), documented versions and generator. | Replace original OSN staging configuration (requires credentials) with local AkôFlow transfers; verify image/data availability. |
| [Orcasound](https://github.com/pegasus-isi/orcasound-workflow) | Hydrophone recordings and orca audio processing/ML. | Generator, processing and ML Dockerfiles, sensor and date selectors. | Confirm recording/model access and image availability. Original README requires AWS credentials for S3 and 16 GB memory, so this is less self-contained. |

Priority after Earthquake: SRA Search, then Variant Calling. Both provide concrete accession lists and references for meaningful biological processing. Orcasound requires additional data-access validation.

WfCommons execution instances remain useful for measured scheduling traces, but are not a substitute for executable programs, input observations and their dependencies.
