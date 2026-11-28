FROM gcc:12.5-bookworm@sha256:3d8481d1f6831bdc43e7973c00b6af00298ec2de392f10ae879e652f185e956f AS compiler
WORKDIR /build
ADD --checksum=sha256:73bbc64b83615aba173cbe9c0af56c1b6b3917cd8e42d9fa5008547dba6aff9b https://raw.githubusercontent.com/UFFeScience/akoflow-examples/17b9ff84800890ab6c0c0ec1a3168c0224ec44d8/computational-fluid-dynamics/lbm-shear-wave/src/shear_wave.cpp /build/shear_wave.cpp
RUN g++ -std=c++20 -O2 -fopenmp -static -Wall -Wextra -Werror shear_wave.cpp -o shear-wave

FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
ADD --checksum=sha256:0fc79f6b55eed5586701557586857304db2d34a4bdb600acde3ba3369bbea236 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/17b9ff84800890ab6c0c0ec1a3168c0224ec44d8/computational-fluid-dynamics/lbm-shear-wave/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock
COPY --from=compiler /build/shear-wave /app/shear-wave
ADD --checksum=sha256:f36b7bf6b2f4919a958970dc7f793ba407fdfa9f56cd950a8c6521adca1f3e55 https://raw.githubusercontent.com/UFFeScience/akoflow-examples/17b9ff84800890ab6c0c0ec1a3168c0224ec44d8/computational-fluid-dynamics/lbm-shear-wave/scripts/aggregate.py /app/scripts/aggregate.py
