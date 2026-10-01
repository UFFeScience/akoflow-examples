FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY scripts/pipeline.py /app/scripts/pipeline.py
ENTRYPOINT ["python", "/app/scripts/pipeline.py"]

