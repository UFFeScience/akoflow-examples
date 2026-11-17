FROM opendronemap/odm@sha256:ca5634e99e711b67e082c7493d2ad5573b0edff3f7e521661f94b99a992f5df1
ENV PYTHONPATH=/code:/code/SuperBuild/install/lib/python3.9/dist-packages:/code/SuperBuild/install/lib/python3.8/dist-packages:/code/SuperBuild/install/bin/opensfm PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg
COPY scripts /app/scripts
COPY data /app/data
ENV PYTHONUNBUFFERED=1
ENTRYPOINT []
CMD []
