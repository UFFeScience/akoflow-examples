FROM python:3.11.13-slim-bookworm@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1
RUN apt-get update && apt-get install -y --no-install-recommends bowtie2=2.5.0-3+b2 samtools=1.16.1-1 && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY scripts /app/scripts
COPY data /app/data
