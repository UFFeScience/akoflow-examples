FROM mambaorg/micromamba@sha256:8d0d4cad074afe3ac93b58dce88bd2659153d3fa6de3a6968f501710e8d3c832 AS mamba
FROM debian@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc AS runtime
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MAMBA_ROOT_PREFIX=/opt/micromamba NXF_HOME=/opt/nextflowhome
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-numpy python3-pandas python3-matplotlib python3-yaml openjdk-17-jre-headless curl bzip2 gzip tar procps git unzip ca-certificates fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY --from=mamba /usr/bin/micromamba /usr/local/bin/micromamba
COPY nextflow /usr/local/bin/nextflow
RUN nextflow -version && nextflow plugin install nf-schema@2.7.2
COPY upstream /app/upstream/rnaseq
COPY prepare-envs.sh /tmp/prepare-envs.sh
RUN bash /tmp/prepare-envs.sh
WORKDIR /app

RUN micromamba create -y -p /opt/nf-envs/samtools-faidx -f /app/upstream/rnaseq/modules/nf-core/samtools/faidx/environment.yml && micromamba env export -p /opt/nf-envs/samtools-faidx --explicit > /opt/nf-env-locks/samtools-faidx.txt && micromamba create -y -p /opt/nf-envs/ea-utils-gtf2bed -f /app/upstream/rnaseq/modules/nf-core/ea-utils/gtf2bed/environment.yml && micromamba env export -p /opt/nf-envs/ea-utils-gtf2bed --explicit > /opt/nf-env-locks/ea-utils-gtf2bed.txt && micromamba clean --all --yes

FROM runtime AS workflow
COPY scripts /app/scripts
COPY data /app/data
COPY config /app/config
COPY workflow.json /app/workflow.json
ENV NXF_OFFLINE=true
