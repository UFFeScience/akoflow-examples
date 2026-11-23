FROM python:3.11-slim-bookworm@sha256:a83ba18aef0f865b1a4a611c2cf460fe446f2795673bbb9fe43be570439e3b39

ENV MPLBACKEND=Agg \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    ASTROML_DATA=/opt/astroml-data

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir 'https://github.com/astroML/gatspy/archive/71384b8d15531bc01a6b85250a35cd675edccf44.zip'
COPY scripts/workflow.py /app/workflow.py
# This is the separately declared networked input-preparation layer. Upstream
# archives remain in the image; scientific activities run with network disabled.
RUN python /app/workflow.py prepare-image-inputs --output /opt/frozen-input
