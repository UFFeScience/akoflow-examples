FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ENV MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib NUMBA_CACHE_DIR=/tmp/numba-cache OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY LICENSE /app/LICENSE
COPY scripts/workflow.py /app/workflow.py
