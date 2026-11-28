FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
ADD --checksum=sha256:6556879f3013df0cd307f2a83c2591aead07bd8fe079fae63136b7ced491b09d https://raw.githubusercontent.com/UFFeScience/akoflow-examples/9d6ca9405439e62026827820e3b76cb00b6196a3/remote-sensing/panchromatic-classification/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock
ADD --checksum=sha256:5433f47087dff42c8aaaf233d6b8fa4ffd1d79b86b0540baa929fd4b2372f656 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/9d6ca9405439e62026827820e3b76cb00b6196a3/remote-sensing/panchromatic-classification/fusion.py /app/fusion.py
ADD --checksum=sha256:d8745d32db1609e774d0a518aa4294f58bfef3c4e56311b1bd3656e126bb6a71 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/9d6ca9405439e62026827820e3b76cb00b6196a3/remote-sensing/panchromatic-classification/render.py /app/render.py
ADD --checksum=sha256:fa58cb96729415d00d62ad0b4cc69d3a77120dfbd0635563d2377564438e3c1b https://raw.githubusercontent.com/UFFeScience/akoflow-examples/9d6ca9405439e62026827820e3b76cb00b6196a3/remote-sensing/panchromatic-classification/aggregate.py /app/aggregate.py
