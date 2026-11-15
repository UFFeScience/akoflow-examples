FROM rust:1.90-slim-bookworm AS rust
FROM python:3.11-slim-bookworm AS wheels
COPY --from=rust /usr/local/cargo /usr/local/cargo
COPY --from=rust /usr/local/rustup /usr/local/rustup
ENV PATH=/usr/local/cargo/bin:$PATH RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo
RUN apt-get update && apt-get install -y --no-install-recommends build-essential pkg-config libssl-dev liblzma-dev ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.lock /tmp/requirements.txt
RUN pip wheel --wheel-dir=/wheels -r /tmp/requirements.txt
FROM python:3.11-slim-bookworm
LABEL org.opencontainers.image.source="https://github.com/UFFeScience/akoflow-examples" org.opencontainers.image.title="AkôFlow OpenOil ensemble" org.opencontainers.image.licenses="GPL-2.0-or-later"
ENV MPLBACKEND=Agg PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 HOME=/tmp
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 liblzma5 libssl3 libgeos-c1v5 ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY --from=wheels /wheels /wheels
COPY requirements.lock /tmp/requirements.txt
RUN pip install --no-index --find-links=/wheels -r /tmp/requirements.txt && pip check && pip freeze > /opt/dependency-lock.txt && rm -rf /wheels
COPY app /opt/openoil
WORKDIR /work
CMD ["python", "/opt/openoil/workflow.py", "--help"]
