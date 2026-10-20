FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
COPY data/input.json /app/scenario.json
COPY scripts/run_showcase.py /app/run_showcase.py
COPY data/ /app/data/
