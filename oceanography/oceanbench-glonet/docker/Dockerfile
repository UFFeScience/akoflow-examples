FROM python@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
ENV PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates gcc g++ \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "git+https://github.com/mercator-ocean/oceanbench.git@61aea40e13689b3dbb0592a74dbf716f15882f5b"
COPY requirements.txt /tmp/community-requirements.txt
RUN pip install --no-cache-dir -r /tmp/community-requirements.txt
COPY inputs/ /inputs/
COPY scripts/workflow.py /app/workflow.py
WORKDIR /work
