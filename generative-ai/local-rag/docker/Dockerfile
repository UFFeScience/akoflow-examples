FROM python:3.12-slim
WORKDIR /app
COPY data /app/data
COPY scripts/pipeline.py /app/scripts/pipeline.py
ENTRYPOINT ["python", "/app/scripts/pipeline.py"]

