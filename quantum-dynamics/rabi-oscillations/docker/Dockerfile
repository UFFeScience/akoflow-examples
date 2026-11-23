FROM python:3.11.14-slim-bookworm
ENV PYTHONHASHSEED=0 MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
WORKDIR /app
COPY requirements.txt LICENSE /app/
RUN pip install --no-cache-dir --requirement requirements.txt
COPY scripts/workflow.py /app/workflow.py
CMD ["python3"]
