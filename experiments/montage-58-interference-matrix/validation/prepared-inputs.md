# Prepared `mDiffFit` inputs

Functional validation performed on 2026-09-30 with the pinned Montage `050d`
image. The calibration image ID was:

`sha256:3bca475f93d3f6889b60b955e2ebd9f109c27bbc8edda180ecf24177f2e62763`

The two `mProject` commands completed successfully and stored these immutable
inputs in `/akoflow-wfa-shared` inside the calibration image:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `pposs2ukstu_blue_001_001.fits` | 53,213,760 | `19a9c21fc81f2f364d774d2e95498855114d7d50b49528c80e3d2bcf8a6684a3` |
| `pposs2ukstu_blue_001_002.fits` | 53,193,600 | `c50fe09cb04ab7faab87623aadc67785f05965420a076b5d0f1f89d5eddfd80b` |
| `region-oversized.hdr` | 277 | `ab4d0ce04df6238607f0248451c13cc4fc3b8e44705b3a9dc7520f10c8a5996f` |

`mDiffFit` was then executed by itself against these files. It completed with
exit status zero, produced non-empty `mdifffit.txt` and `mdifffit.fits`, and
took 1.665398375 seconds inside the measured command window.

This was a functional check on Docker Desktop running the `linux/amd64` image
through an ARM host. The duration is not a cloud or local calibration sample
and must not be included in the interference matrix. The committed Dockerfile
and preparation script reproduce the inputs natively on each approved amd64
environment before measurements begin.
