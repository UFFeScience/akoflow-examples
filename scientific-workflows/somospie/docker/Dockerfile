FROM debian@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc AS runtime
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-numpy python3-scipy python3-pandas python3-sklearn python3-matplotlib python3-netcdf4 python3-gdal python3-pil gdal-bin ca-certificates fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM runtime AS workflow
COPY scripts /app/scripts
COPY data /app/data
COPY workflow.json /app/workflow.json
