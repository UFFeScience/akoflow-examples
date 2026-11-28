FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
ADD --checksum=sha256:9ccc005ed2983c7009cc526b9b8fccde9cb431021ca8216c67b5022bd776baa0 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/e95a6b18d5892eda5ff672ad8e46f45315e54604/geospatial/synthetic-idw-audit/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
ADD --checksum=sha256:920a592a25492f728aa618447e32a7c4188310f3f62ff9da3e2b7239e9181791 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/e95a6b18d5892eda5ff672ad8e46f45315e54604/geospatial/synthetic-idw-audit/scripts/study.py /app/scripts/study.py
ADD --checksum=sha256:53d30098e252a7ac5ad4bdcbaa8c002fba54d98dca4dead050c1504fab333d0f https://raw.githubusercontent.com/UFFeScience/akoflow-examples/e95a6b18d5892eda5ff672ad8e46f45315e54604/geospatial/synthetic-idw-audit/scripts/render.py /app/scripts/render.py
ADD --checksum=sha256:c42bb1130013b27d35607992836ba3945e34a5cf4a4a95dbaba4bad5ee9103f9 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/e95a6b18d5892eda5ff672ad8e46f45315e54604/geospatial/synthetic-idw-audit/evidence/samples.json /app/evidence/samples.json
ADD --checksum=sha256:43ee7ca1c66372ca0a7fb726f657ef13a68cf1a34b5b4694fdf1d917f9ed3a74 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/e95a6b18d5892eda5ff672ad8e46f45315e54604/geospatial/synthetic-idw-audit/evidence/samples.sha256 /app/evidence/samples.sha256
