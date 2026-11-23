FROM python:3.10.14-slim-bookworm@sha256:5be5aaecb962a41567bc8041f1e9e3432cb085b037fe057f9a562630b2e4b370

ARG BIOCLIP_COMMIT=7555b4e00583687b128a12df2e0b70e6a7bc1522
ARG BIOCLIP_ARCHIVE_SHA256=7f5dab814208c2921b018d4eb179371339e1318de453c2e02dca6c492343d031
ARG MODEL_REVISION=799f1d9eb01abf82c9353de5951967755315725f
ARG DATASET_REVISION=59689732c07819c9472b6a2ef5b9da9b473f7c27
ARG BIOCLIP_DATA_MIRROR=

ENV PYTHONHASHSEED=0 \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    NUMEXPR_NUM_THREADS=2 \
    MPLBACKEND=Agg \
    PYTHONPATH=/opt/bioclip \
    BIOCLIP_DATA_MIRROR=${BIOCLIP_DATA_MIRROR}

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --timeout 120 --retries 12 -r /tmp/requirements.txt

RUN curl -fsSL "https://codeload.github.com/Imageomics/bioclip/tar.gz/${BIOCLIP_COMMIT}" -o /tmp/bioclip.tar.gz \
    && echo "${BIOCLIP_ARCHIVE_SHA256}  /tmp/bioclip.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/bioclip \
    && tar -xzf /tmp/bioclip.tar.gz --strip-components=1 -C /opt/bioclip \
    && rm /tmp/bioclip.tar.gz

RUN mkdir -p /opt/bioclip/model /opt/bioclip/assets \
    && for file in open_clip_config.json open_clip_pytorch_model.bin merges.txt special_tokens_map.json tokenizer.json tokenizer_config.json vocab.json; do \
         curl -fsSL --retry 12 --retry-delay 3 \
           "https://huggingface.co/imageomics/bioclip/resolve/${MODEL_REVISION}/${file}" \
           -o "/opt/bioclip/model/${file}"; \
       done \
    && echo "e380384f0c30d425d8c6c40f24471f9dd497fbdfa734a89c461a94aee95f0ef4  /opt/bioclip/model/open_clip_pytorch_model.bin" | sha256sum -c - \
    && echo "86d418d7046fa9212ab70eb7cb3deeef02be46f39d7948bad5dc7649f8277208  /opt/bioclip/model/open_clip_config.json" | sha256sum -c - \
    && echo "d8b124290bc4bcd18cd3f72747f525e2a1d8c266cf3089e52da38ee417564ac5  /opt/bioclip/model/tokenizer.json" | sha256sum -c -

RUN curl -fsSL --retry 12 --retry-delay 3 \
      "https://huggingface.co/datasets/imageomics/rare-species/resolve/${DATASET_REVISION}/metadata/rarespecies-catalog.csv" \
      -o /opt/bioclip/assets/rarespecies-catalog.csv \
    && curl -fsSL --retry 12 --retry-delay 3 \
      "https://huggingface.co/datasets/imageomics/rare-species/resolve/${DATASET_REVISION}/metadata/licenses.csv" \
      -o /opt/bioclip/assets/licenses.csv \
    && echo "96c458bd580caf5df4743c639eb38490e62eddef44b92be519d6771bdc2bf8fa  /opt/bioclip/assets/rarespecies-catalog.csv" | sha256sum -c - \
    && echo "8cd23a637cc8c6c9175b652b9cfdd695060b27d077d1677fd154c992eb09c754  /opt/bioclip/assets/licenses.csv" | sha256sum -c -

RUN curl -fsSL --retry 12 --retry-delay 3 \
      "https://raw.githubusercontent.com/UFFeScience/akoflow-examples/71bed4f/biodiversity/bioclip-rare-species/assets/classifier.pt" \
      -o /opt/bioclip/assets/classifier.pt \
    && echo "7ca30fa6c485f8f4a4ba9113db4fb272ad839927bd7f5e649d412f33a1bd2f42  /opt/bioclip/assets/classifier.pt" | sha256sum -c -

COPY scripts/workflow.py /app/workflow.py
WORKDIR /work
