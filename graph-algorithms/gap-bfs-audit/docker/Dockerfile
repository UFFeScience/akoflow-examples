FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ENV OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl g++ && apt-get clean
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN curl -fsSL https://codeload.github.com/sbeamer/gapbs/tar.gz/941462c7c42e786e4e006a9211b0576ef78d23f7 -o /tmp/gapbs.tar.gz \
    && echo '2a5fc6417768ae488b5b0e36ea5bc00b9c6400fcce8349e7e14acfaeb33dc778  /tmp/gapbs.tar.gz' | sha256sum -c - \
    && mkdir /tmp/gapbs && tar -xzf /tmp/gapbs.tar.gz --strip-components=1 -C /tmp/gapbs \
    && cp /tmp/gapbs/LICENSE /app/GAPBS-LICENSE
COPY src/audit.cc /app/audit.cc
RUN g++ -std=c++11 -O3 -Wall -fopenmp -I /tmp/gapbs/src /app/audit.cc -o /app/bfs-audit
COPY scripts /app/scripts
RUN chmod -R a+rX /app
