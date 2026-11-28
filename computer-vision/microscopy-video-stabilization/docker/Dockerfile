FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
ADD --checksum=sha256:6556879f3013df0cd307f2a83c2591aead07bd8fe079fae63136b7ced491b09d https://raw.githubusercontent.com/UFFeScience/akoflow-examples/3127008e293f127d4ad77e6aa13e7079d8458936/computer-vision/microscopy-video-stabilization/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock
ADD --checksum=sha256:433f912b3b5df90b093c5c2de13ddec2fa03639fc6a9167c33def18da810a011 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/3127008e293f127d4ad77e6aa13e7079d8458936/computer-vision/microscopy-video-stabilization/stabilize.py /app/stabilize.py
ADD --checksum=sha256:67a232ad23868bc51e2bb26e832db9a8035cae100e0e8392b0ce074f86230f36 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/3127008e293f127d4ad77e6aa13e7079d8458936/computer-vision/microscopy-video-stabilization/render.py /app/render.py
ADD --checksum=sha256:5893aa3887e17eadd923018bbac4aff72001a9f813e82b4a9ed22a946555f521 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/3127008e293f127d4ad77e6aa13e7079d8458936/computer-vision/microscopy-video-stabilization/aggregate.py /app/aggregate.py
