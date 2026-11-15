FROM python@sha256:a83ba18aef0f865b1a4a611c2cf460fe446f2795673bbb9fe43be570439e3b39 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libfftw3-double3 libfftw3-single3 libgsl27 ca-certificates fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir PyCBC==2.10.0 numpy==1.26.4 scipy==1.15.3 matplotlib==3.10.3 h5py==3.13.0 pyfftw==0.15.1
RUN pip check && pip freeze > /opt/python-dependencies.lock && python -c "import pycbc,lal,h5py; print(pycbc.__version__,lal.__version__,h5py.__version__)"
WORKDIR /app

FROM runtime AS workflow
COPY scripts /app/scripts
COPY data /app/data
COPY workflow.json /app/workflow.json
