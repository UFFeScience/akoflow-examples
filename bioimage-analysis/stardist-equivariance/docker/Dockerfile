FROM python:3.10.14-slim-bookworm@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3

ARG STARDIST_COMMIT=e80c6de700693bc228ed3c9ba1dc19c3785667ee
ARG STARDIST_ARCHIVE_SHA256=4b0b408717538640396cb44807b975f0c6d7af3d278904f19a2b1b7972609ffb

ENV PYTHONHASHSEED=20261122 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    TF_ENABLE_ONEDNN_OPTS=0 \
    TF_DETERMINISTIC_OPS=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    MPLBACKEND=Agg

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential ca-certificates curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN curl -fsSL "https://codeload.github.com/stardist/stardist/tar.gz/${STARDIST_COMMIT}" -o /tmp/stardist.tar.gz \
    && echo "${STARDIST_ARCHIVE_SHA256}  /tmp/stardist.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/stardist \
    && tar -xzf /tmp/stardist.tar.gz --strip-components=1 -C /opt/stardist \
    && pip install --no-cache-dir --no-deps /opt/stardist \
    && rm /tmp/stardist.tar.gz

COPY scripts/workflow.py /app/workflow.py
WORKDIR /work
