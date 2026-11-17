FROM python:3.11.13-slim-bookworm@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1
ENV MPLBACKEND=Agg OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-15 build-essential libcurl4 && useradd --uid 1000 --no-create-home scientist && rm -rf /var/lib/apt/lists/*
COPY scripts /app/scripts
COPY data /app/data
RUN mkdir -p /opt/dbgen /opt/mongodb && tar -xzf /app/data/inputs/dbgen.tar.gz -C /opt/dbgen --strip-components=1 && make -C /opt/dbgen -f makefile.suite CC=gcc DATABASE=ORACLE MACHINE=LINUX WORKLOAD=TPCH && tar -xzf /app/data/inputs/mongodb.tgz -C /opt/mongodb --strip-components=1
ENV PATH=/usr/lib/postgresql/15/bin:/opt/mongodb/bin:$PATH DSS_CONFIG=/opt/dbgen
