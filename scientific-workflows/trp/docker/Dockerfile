FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 LOKY_MAX_CPU_COUNT=2
RUN apt-get update && apt-get install -y --no-install-recommends r-base-core r-base-dev r-bioc-edger=3.40.2+dfsg-1 r-cran-statmod libffi-dev libcurl4-openssl-dev libssl-dev libxml2-dev build-essential ca-certificates fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
LABEL org.opencontainers.image.source="https://github.com/UFFeScience/akoflow-examples"
LABEL org.opencontainers.image.title="TRP TCGA-BRCA six-stage scientific workflow"
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY upstream /app/upstream
COPY scripts /app/scripts
COPY data /app/data
