#!/bin/bash
set -euo pipefail
mkdir -p /opt/nf-env-locks
micromamba create -y -p /opt/nf-envs/cat-fastq -f /app/upstream/rnaseq/modules/nf-core/cat/fastq/environment.yml
micromamba env export -p /opt/nf-envs/cat-fastq --explicit > /opt/nf-env-locks/cat-fastq.txt
micromamba create -y -p /opt/nf-envs/fq-lint -f /app/upstream/rnaseq/modules/nf-core/fq/lint/environment.yml
micromamba env export -p /opt/nf-envs/fq-lint --explicit > /opt/nf-env-locks/fq-lint.txt
micromamba create -y -p /opt/nf-envs/fq-subsample -f /app/upstream/rnaseq/modules/nf-core/fq/subsample/environment.yml
micromamba env export -p /opt/nf-envs/fq-subsample --explicit > /opt/nf-env-locks/fq-subsample.txt
micromamba create -y -p /opt/nf-envs/fastqc -f /app/upstream/rnaseq/modules/nf-core/fastqc/environment.yml
micromamba env export -p /opt/nf-envs/fastqc --explicit > /opt/nf-env-locks/fastqc.txt
micromamba create -y -p /opt/nf-envs/fastp -f /app/upstream/rnaseq/modules/nf-core/fastp/environment.yml
micromamba env export -p /opt/nf-envs/fastp --explicit > /opt/nf-env-locks/fastp.txt
micromamba create -y -p /opt/nf-envs/trimgalore -f /app/upstream/rnaseq/modules/nf-core/trimgalore/environment.yml
micromamba env export -p /opt/nf-envs/trimgalore --explicit > /opt/nf-env-locks/trimgalore.txt
micromamba create -y -p /opt/nf-envs/gunzip -f /app/upstream/rnaseq/modules/nf-core/gunzip/environment.yml
micromamba env export -p /opt/nf-envs/gunzip --explicit > /opt/nf-env-locks/gunzip.txt
micromamba create -y -p /opt/nf-envs/gffread -f /app/upstream/rnaseq/modules/nf-core/gffread/environment.yml
micromamba env export -p /opt/nf-envs/gffread --explicit > /opt/nf-env-locks/gffread.txt
micromamba create -y -p /opt/nf-envs/custom-gtffilter -f /app/upstream/rnaseq/modules/nf-core/custom/gtffilter/environment.yml
micromamba env export -p /opt/nf-envs/custom-gtffilter --explicit > /opt/nf-env-locks/custom-gtffilter.txt
micromamba create -y -p /opt/nf-envs/custom-tx2gene -f /app/upstream/rnaseq/modules/nf-core/custom/tx2gene/environment.yml
micromamba env export -p /opt/nf-envs/custom-tx2gene --explicit > /opt/nf-env-locks/custom-tx2gene.txt
micromamba create -y -p /opt/nf-envs/salmon-index -f /app/upstream/rnaseq/modules/nf-core/salmon/index/environment.yml
micromamba env export -p /opt/nf-envs/salmon-index --explicit > /opt/nf-env-locks/salmon-index.txt
micromamba create -y -p /opt/nf-envs/salmon-quant -f /app/upstream/rnaseq/modules/nf-core/salmon/quant/environment.yml
micromamba env export -p /opt/nf-envs/salmon-quant --explicit > /opt/nf-env-locks/salmon-quant.txt
micromamba create -y -p /opt/nf-envs/tximeta-tximport -f /app/upstream/rnaseq/modules/nf-core/tximeta/tximport/environment.yml
micromamba env export -p /opt/nf-envs/tximeta-tximport --explicit > /opt/nf-env-locks/tximeta-tximport.txt
micromamba create -y -p /opt/nf-envs/multiqc -f /app/upstream/rnaseq/modules/nf-core/multiqc/environment.yml
micromamba env export -p /opt/nf-envs/multiqc --explicit > /opt/nf-env-locks/multiqc.txt
micromamba clean --all --yes
