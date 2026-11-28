FROM gcc:12.5-bookworm@sha256:3d8481d1f6831bdc43e7973c00b6af00298ec2de392f10ae879e652f185e956f AS compiler
WORKDIR /build
COPY src/shear_wave.cpp .
RUN g++ -std=c++20 -O2 -fopenmp -static -Wall -Wextra -Werror shear_wave.cpp -o shear-wave

FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock
COPY --from=compiler /build/shear-wave /app/shear-wave
COPY scripts/aggregate.py /app/scripts/aggregate.py
