FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
ENV PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
RUN pip install --no-cache-dir numpy==2.1.3 matplotlib==3.9.2 pillow==11.0.0
WORKDIR /app
COPY scripts/workflow.py /app/workflow.py
