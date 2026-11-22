FROM python:3.10-slim-bookworm@sha256:5be5aaecb962a41567bc8041f1e9e3432cb085b037fe057f9a562630b2e4b370
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    MPLCONFIGDIR=/tmp/matplotlib
RUN pip install --timeout 1000 --retries 8 --no-cache-dir \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      numpy==1.24.4 torch==1.13.1+cpu matplotlib==3.7.5 Pillow==10.4.0
WORKDIR /app
COPY scripts/ /app/
COPY inputs/ /inputs/
