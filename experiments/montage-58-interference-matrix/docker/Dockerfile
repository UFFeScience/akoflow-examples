ARG BASE_IMAGE=ovvesley/akoflow-wf-montage@sha256:26b060b83b990557ea86ab40503cc8f17ab6016b5973e7e6f9201100a96440c9
FROM ${BASE_IMAGE}

WORKDIR /akoflow-wfa-shared

# mDiffFit consumes projected FITS files. Materialize the two inputs while the
# calibration image is built so projection time is outside every measured run.
RUN mProject -X \
      poss2ukstu_blue_001_001.fits \
      pposs2ukstu_blue_001_001.fits \
      region-oversized.hdr \
 && mProject -X \
      poss2ukstu_blue_001_002.fits \
      pposs2ukstu_blue_001_002.fits \
      region-oversized.hdr
