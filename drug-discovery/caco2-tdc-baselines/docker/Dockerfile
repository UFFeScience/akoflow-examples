FROM python:3.10.14-slim-bookworm@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3

ARG DEEPPURPOSE_COMMIT=866be98bad0b11e78d4363589b9ee59b5befa307
ARG DEEPPURPOSE_ARCHIVE_SHA256=3dbeb34970cfb9209e25cd2336d7569ba673f7d9e0989c7a617e2c2598283d4d
ARG ADMET_GROUP_FILE_ID=4426004
ARG ADMET_GROUP_SHA256=bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1

ENV PYTHONHASHSEED=20261122 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    MPLBACKEND=Agg \
    PYTHONPATH=/opt/DeepPurpose

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN curl -fsSL "https://codeload.github.com/kexinhuang12345/DeepPurpose/tar.gz/${DEEPPURPOSE_COMMIT}" -o /tmp/deeppurpose.tar.gz \
    && echo "${DEEPPURPOSE_ARCHIVE_SHA256}  /tmp/deeppurpose.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/DeepPurpose \
    && tar -xzf /tmp/deeppurpose.tar.gz --strip-components=1 -C /opt/DeepPurpose \
    && rm /tmp/deeppurpose.tar.gz

RUN curl -fsSL "https://dataverse.harvard.edu/api/access/datafile/${ADMET_GROUP_FILE_ID}" -o /tmp/admet-group.zip \
    && echo "${ADMET_GROUP_SHA256}  /tmp/admet-group.zip" | sha256sum -c - \
    && python -c "import zipfile; z=zipfile.ZipFile('/tmp/admet-group.zip'); [z.extract(n, '/opt/tdc') for n in z.namelist() if '/caco2_wang/' in n]" \
    && test "$(sha256sum /opt/tdc/admet_group/caco2_wang/train_val.csv | cut -d' ' -f1)" = e0965b4a0617a3aa2978ef28794e3467d55655090f282a120355ea575ebed6b2 \
    && test "$(sha256sum /opt/tdc/admet_group/caco2_wang/test.csv | cut -d' ' -f1)" = 5380c15b0dd9c11e22d3e3843083362d535dae36062dfee08056d3af4cb444df \
    && rm /tmp/admet-group.zip

COPY scripts/workflow.py /app/workflow.py
WORKDIR /work
