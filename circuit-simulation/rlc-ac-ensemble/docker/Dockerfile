FROM ubuntu:26.04@sha256:0d5255be560e2d2ddcfbfda88549e9e815ef29e7cd7fc62183d5709e6e2963c6
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-matplotlib python3-pil \
    && apt-get download ngspice=45.2+ds-1 \
    && echo '08aa3c21ca2390ae68521ccb3545de76663ebfbc643b7bfd87c9320969730fb2  ngspice_45.2+ds-1_amd64.deb' | sha256sum -c - \
    && apt-get install -y --no-install-recommends ./ngspice_45.2+ds-1_amd64.deb \
    && rm ngspice_45.2+ds-1_amd64.deb && apt-get clean
COPY scripts /app/scripts
RUN chmod -R a+rX /app
