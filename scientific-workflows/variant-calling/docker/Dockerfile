FROM pegasus/variant-calling@sha256:b38fb01e141061a12d13078accd2b116fb1a86081dc2b170658ff1c6f8737f6a
ENV PYTHONDONTWRITEBYTECODE=1 LC_ALL=C
WORKDIR /app
COPY scripts /app/scripts
COPY data /app/data
COPY workflow.json /app/workflow.json
