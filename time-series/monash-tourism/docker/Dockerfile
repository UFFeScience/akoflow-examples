FROM debian:bookworm-slim@sha256:e67eeead736ff7bbe258ef088bff683635c561b1fcfefad0806c1df4ab49ce0e
ENV LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends r-base-core=4.2.2.20221110-2 r-cran-forecast=8.20-1 unzip imagemagick && apt-get clean
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY data /app/data
COPY scripts /app/scripts
RUN chmod -R a+rX /app
