# Airy circular-aperture diffraction and encircled-energy audit

This deterministic CPU workflow reproduces George Biddell Airy's ideal circular-aperture radial intensity law, `I(u)=[2 J1(u)/u]^2`, and checks the first dark ring, wavelength scaling, and encircled energy at 450, 550, and 650 nm. It uses an 80-significant-digit standard-library Decimal series to avoid the large-argument cancellation found during qualification.

![Airy radial intensity and encircled-energy profiles](outputs/reference/airy-profiles.png)

*The scientific profile figure shows the shared dimensionless diffraction law evaluated independently by all three wavelength branches; physical dark-ring radii scale with wavelength.*

![450 nm point-spread function](outputs/reference/450nm-psf.png)

*The 1024×1024 450 nm focal-plane image spans ±4 λf/D. The corresponding 550 and 650 nm PSFs are retained beside it as independently generated results.*

![Wavelength sweep of the ideal Airy pattern](outputs/reference/wavelength-sweep.gif)

*The fixed-axis animation visualizes analytic wavelength scaling from 450 to 650 nm; its interpolated frames are presentation artifacts, not additional executed scientific branches.*

## Validated result

All three daemon branches recovered `j(1,1)=3.831705970207512`, with `|J1(root)|=1.17e-16`. The central-disk encircled energy is `0.8377848691733144`; independent 131,072-subinterval Simpson quadrature differs by about `7.8e-15`. Each branch emitted 20,001 ordered radial samples, used at most 76 series terms, passed the fixed integral checkpoints, and produced byte-identical dimensionless intensity and energy columns. The first-dark-ring radii are 5.4885, 6.7082, and 7.9279 micrometres for 450, 550, and 650 nm respectively.

## Measured AkôFlow execution

Portable daemon run `community-airy-diffraction-run-v2` rebuilt the missing
image and completed all seven activities in `95.6172 s`. The three independent
wavelength evaluations overlapped for `10.3308 s` on three distinct declared
resources. The matched one-slot run
`community-airy-diffraction-one-slot-v2` completed in `118.4057 s`; the
observed whole-workflow ratio was `1.2383×`. This is a measured result for this
host and scenario, not a general scaling claim.

![Measured AkôFlow DAG](evidence/measured-dag.png)

*The measured workflow DAG fans out into three scientific wavelength evaluations and joins for scaling, rendering, and validation.*

![Measured AkôFlow timeline](evidence/measured-timeline.png)

*The timeline is rendered from persisted daemon timestamps and records actual overlap among the 450, 550, and 650 nm evaluations.*

## Reproduce

```sh
./build.sh
./preflight.sh
./run.sh
AKOFLOW_SUBMIT=1 ./run.sh
```

The image is pinned to Python 3.11.14 and uses only its standard library. Scientific execution is offline and receives neither Hub credentials nor the host Docker socket. A helper run is only preflight; the recorded daemon runs above are execution evidence.

The imported workflow resolves all seven activities from one immutable AkôFlow
build recipe. Its archived context contains `docker/Dockerfile`,
`requirements.txt`, `LICENSE`, and `scripts/workflow.py`; every `COPY` source is
contained and the base image is pinned by digest. From an unmaterialized state,
preflight reported `Build required`, and AkôFlow reconstructed and verified the
OCI image before running the DAG. The context digest is
`sha256:ca3624f437e80ff8c0556a5d4cb3d2fba9d90bbd33079eb65e25c8ba3c2f7a48`;
the recipe digest is
`sha256:3bb32dd151f398c29f75e2d5fab9c11a8484aa1bddda251b45fdbabb2b026863`.

## Public Community Explorer record

[Open the public workflow and measured results](https://hub.akoflow.com/o/akoflow/community-explorer-issue-37-airy-diffraction-v1).
Import portable version 2 with
`akoflow://hub/publications/57999cfa-0c42-46ad-98c8-2e2547c41839/versions/2`.

## Interpretation and limitations

This is an ideal scalar, monochromatic, paraxial, unobscured circular aperture. It does not model aberrations, central obscuration, spiders, atmospheric seeing, vector diffraction, finite bandwidth, detector sampling, or a measured telescope. The animation interpolates wavelength only after the independently evaluated reference branches.

## Citation, authorship, and license

Scientific source: George Biddell Airy, “On the Diffraction of an Object-glass with Circular Aperture,” *Transactions of the Cambridge Philosophical Society* 5 (1835), 283–291. Bessel zeros and radial integral identities are cross-checked against [NIST DLMF §10.21](https://dlmf.nist.gov/10.21) and [§10.22](https://dlmf.nist.gov/10.22). Sources are linked, not redistributed.

The original workflow code and generated artifacts are maintained by UFFeScience for AkôFlow Community Explorer under the MIT License. Python is distributed under the PSF License.
