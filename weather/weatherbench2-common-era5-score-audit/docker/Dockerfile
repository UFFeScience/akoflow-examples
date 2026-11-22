FROM python:3.11-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/workflow.py input-manifest.json ./
COPY data/ ./data/
ENV MPLCONFIGDIR=/tmp/matplotlib
