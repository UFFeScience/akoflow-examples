FROM ubuntu:24.04@sha256:9c7f200c07e3d4a03e7249d2c16bf66a51120fb876aa2242cf31451412543289

ARG MFC_REVISION=06f4418d675016d11df14a05de8b1c32e878de92
ARG MFC_ARCHIVE_SHA256=a6c239a94875294ecd6a8395aee9cb36e3dc6a31ffb99d0551de890e121da118

ENV DEBIAN_FRONTEND=noninteractive \
    MPLBACKEND=Agg \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl patch python3 python3-pip python3-venv \
      gcc g++ gfortran cmake make openmpi-bin libopenmpi-dev \
      libhdf5-openmpi-dev libfftw3-dev libsilo-dev libstdc++-13-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN curl --fail --location --retry 5 \
      "https://github.com/MFlowCode/MFC/archive/${MFC_REVISION}.tar.gz" \
      --output /tmp/mfc.tar.gz \
    && echo "${MFC_ARCHIVE_SHA256}  /tmp/mfc.tar.gz" | sha256sum --check - \
    && tar -xzf /tmp/mfc.tar.gz \
    && mv "MFC-${MFC_REVISION}" mfc \
    && rm /tmp/mfc.tar.gz

COPY docker/postprocess-stdcxx.patch /tmp/postprocess-stdcxx.patch
RUN cd /opt/mfc \
    && patch -p1 < /tmp/postprocess-stdcxx.patch \
    && ./mfc.sh build -t pre_process simulation post_process -j 1 \
    && rm /tmp/postprocess-stdcxx.patch

COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --break-system-packages --no-cache-dir -r /app/requirements.txt
RUN dpkg-query -W > /opt/dpkg-manifest.txt \
    && python3 -m pip freeze > /opt/python-manifest.txt
COPY scripts/workflow.py /app/workflow.py
COPY LICENSE-MFC /licenses/MFC-MIT.txt
COPY LICENSE-SOD-REFERENCE /licenses/sod-reference-MIT.txt
COPY LICENSE-SILO /licenses/Silo-BSD-3-Clause.txt

WORKDIR /work
