FROM python:3.11.13-slim-bookworm@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1
ENV MPLBACKEND=Agg OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-15 postgresql-15-postgis-3 && rm -rf /var/lib/apt/lists/* && useradd --uid 1000 --no-create-home scientist && useradd --uid 1001 --no-create-home ci-scientist
COPY scripts /app/scripts
COPY data /app/data
ENV PATH=/usr/lib/postgresql/15/bin:$PATH
