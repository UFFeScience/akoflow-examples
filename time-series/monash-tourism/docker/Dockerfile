FROM debian:bookworm-slim@sha256:e67eeead736ff7bbe258ef088bff683635c561b1fcfefad0806c1df4ab49ce0e
ENV LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends r-base-core=4.2.2.20221110-2 r-cran-forecast=8.20-1 unzip imagemagick ca-certificates curl && apt-get clean
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY scripts /app/scripts
RUN chmod -R a+rX /app
RUN mkdir -p /app/data \
    && curl -fsSL https://raw.githubusercontent.com/UFFeScience/akoflow-examples/c25e8caddbdbc5bb48b08d65ac1d397887db042d/time-series/monash-tourism/data/monthly.zip -o /app/data/monthly.zip \
    && curl -fsSL https://raw.githubusercontent.com/UFFeScience/akoflow-examples/c25e8caddbdbc5bb48b08d65ac1d397887db042d/time-series/monash-tourism/data/quarterly.zip -o /app/data/quarterly.zip \
    && curl -fsSL https://raw.githubusercontent.com/UFFeScience/akoflow-examples/c25e8caddbdbc5bb48b08d65ac1d397887db042d/time-series/monash-tourism/data/yearly.zip -o /app/data/yearly.zip \
    && cd /app/data \
    && printf '%s\n' '7b9a152b2736aff87bb5155f6a650693  monthly.zip' 'fc5fa2e1e08103c4b586d5a3bd5097fb  quarterly.zip' 'a0b9b63d7f855e76ac406ffbe9237267  yearly.zip' | md5sum -c -
