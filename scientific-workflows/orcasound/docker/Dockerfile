FROM python@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg OMP_NUM_THREADS=2 HF_HUB_OFFLINE=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1
RUN pip install --no-cache-dir librosa==0.11.0 soundfile==0.13.1 scipy==1.17.0 numpy==2.3.5 pyyaml==6.0.3 pydub==0.25.1 huggingface-hub==1.3.1 safetensors==0.7.0 matplotlib==3.10.8 ffmpeg-python==0.2.0
WORKDIR /app

FROM runtime AS workflow
COPY scripts /app/scripts
COPY data /app/data
COPY workflow.json /app/workflow.json
