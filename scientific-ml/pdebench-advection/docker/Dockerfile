FROM python:3.10-slim-bookworm@sha256:5be5aaecb962a41567bc8041f1e9e3432cb085b037fe057f9a562630b2e4b370
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    MPLCONFIGDIR=/tmp/matplotlib
RUN pip install --timeout 120 --retries 3 --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu --no-deps torch==1.13.1+cpu \
    && pip install --timeout 120 --retries 3 --no-cache-dir \
      numpy==1.24.4 matplotlib==3.7.5 Pillow==10.4.0 'typing-extensions>=4' \
    && pip check
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY scripts/fno.py scripts/unet.py scripts/workflow.py scripts/fetch_inputs.py input-manifest.json /app/
RUN python /app/fetch_inputs.py
