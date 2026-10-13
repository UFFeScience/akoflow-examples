FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends blender ffmpeg python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY scripts /app/scripts
ENTRYPOINT ["python3", "/app/scripts/pipeline.py"]

