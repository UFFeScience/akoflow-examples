# Sod shock tube: parallel mesh refinement with MFC

This CPU-only workflow validates the standard one-dimensional Sod shock tube
with the Multi-component Flow Code (MFC) at 100, 200, 400, and 800
finite-volume cells. It is a bounded numerical-validation adaptation of MFC,
not a reproduction of the SC Workshops 2024 GPU-offload or exascale
performance claims.

## Fixed scientific scenario

The domain is `x in [0,1]`, with a discontinuity at `x=0.5`, ideal-gas
`gamma=1.4`, left state `(rho,u,p)=(1,0,1)`, right state
`(0.125,0,0.1)`, and final time `T=0.1`. The solver matches MFC's official
case: RK3, mapped WENO5, HLLC, direct wave speeds, arithmetic averaging, and
outflow boundaries. Resolution `N` maps to MFC `m=N-1`; `dt=0.04/N`, so the
four branches take 250, 500, 1000, and 2000 steps.

The exact Euler reference is evaluated as finite-volume cell averages. Each
cell is split at analytic wave locations and integrated with deterministic
eight-point Gauss-Legendre quadrature. The independently calculated star
state is `p*=0.30313017805064685`, `u*=0.9274526200489499`.

Validation requires positive density and pressure, mass and total-energy
absolute drift at most `1e-12`, decreasing L1 errors at every refinement,
fitted orders within `0.15` of the qualified values, and aggregate L1 metrics
within `1e-12` of the pre-implementation qualification run. Every simulation
must also produce 22 Silo/HDF5 files from 11 saved states.

## Scientific DAG

`prepare` freezes provenance and licenses. Four independent
`simulate-n{100,200,400,800}` activities run the complete MFC preprocess,
simulation, and postprocess chain, each followed by a matching `measure`
activity. `aggregate` produces convergence and finest-grid scientific figures;
`animate` renders the actual N=800 saved evolution; `validate` joins them.

The four resolution branches are the parallel scientific work. Concurrency
must be demonstrated from AkôFlow daemon timestamps. No speedup claim is made
without a separate matching one-slot execution.

## Reproducible build and execution

MFC is pinned to v4.9.9 revision
`06f4418d675016d11df14a05de8b1c32e878de92`; its revision archive SHA-256 is
`a6c239a94875294ecd6a8395aee9cb36e3dc6a31ffb99d0551de890e121da118`.
The exact-reference lineage is `ibackus/sod-shocktube` revision
`06cd0b8822c52c86d0e9c91e2d214d7e7527c492`, archive SHA-256
`e0ec32bdc83d5f114af345f5949b1d2bd4f1b78a4fc290d441db5afaa5bd87e0`.
The adapted formulas are vendored in `scripts/workflow.py`.

The Ubuntu 24.04 base is digest-pinned. The image records complete dpkg and
Python manifests. Ubuntu's Silo 4.11 library needs the C++ runtime when linked
by MFC's Fortran driver, so the Docker build applies the qualified one-line
non-scientific link correction in `docker/postprocess-stdcxx.patch`. It does
not modify numerical source.

```sh
sudo -n docker build -f docker/Dockerfile \
  -t akoflow/community-mfc-sod-refinement:v1 .
./preflight.sh
# With the official AkôFlow daemon available at port 8080:
./run.sh
```

Image construction is the separately declared networked preparation step.
Scientific activities run offline without Hub credentials or the host Docker
socket. `preflight.sh` is only a local integration check; authoritative
execution evidence must come from the AkôFlow daemon.

## Reference daemon run

AkôFlow run `community-mfc-sod-run-v2` completed all 12 activities using
workflow version `community-mfc-sod-refinement-r2-v1`, schedule plan
`community-mfc-sod-plan-v2`, and image digest
`sha256:f9ee240ddc78b32b7396f486758be073e0c5fa64b0984963856916bcca7f3ee1`.
Measured makespan was 18.782 seconds, compute time was 28.016 seconds, and
14,770,853 bytes were transferred at zero configured cost.

The four independent MFC simulations overlapped from Unix timestamp
`1795330651.065916` through `1795330654.990757`, a measured four-way overlap
of 3.925 seconds. This proves concurrent scientific activity; it is not a
speedup claim because no matched one-slot run was performed.
The timeline renderer records this evidence in `measured-timeline.json` and
`measured-timeline.png`; the reference PNG SHA-256 is
`9f552a84dc6e5c808af540a402643e1d3c028a930e9ae05ec2c26574821f247f`.

The recorded validator passed every scientific and artifact check. Its
SHA-256 is `fd9f5211f171f6365228575c54fffc15fa84c32147c31c6a8e83f49f742dc4f9`;
`metrics.json` is `190e8784c85e3d96d47fc8173d62d9436c5c8cf14d056fb5c0ea45000079ec7e`.
The convergence figure, finest-grid result, and evolution GIF are respectively
`8a688aa958a1fbcc482c10161d91a0434f9cdbc218d3c83cd8c1959f49139321`,
`6f507f9284ef0aed5d262b72b11b5fc7bcf484a0e78e74519876d23d149e6cd5`,
and `332f2ccbcf66e30dc0fdb7d765a9e2cce8bd5efbdf7efdc149f22c9e71afe8b8`.

## Qualified reference values

| N | density L1 | velocity L1 | pressure L1 |
|---:|---:|---:|---:|
| 100 | 0.00332641297392204 | 0.007187011028274121 | 0.002725182919170022 |
| 200 | 0.0017125745723256304 | 0.0039289634156148955 | 0.001491920960328745 |
| 400 | 0.0009536509753016517 | 0.001957833988217819 | 0.0007352216657279762 |
| 800 | 0.00047398891833157783 | 0.0009282408469389935 | 0.0003491277318294909 |

Qualified fitted orders are density `0.927776`, velocity `0.986335`, and
pressure `0.991450`. These values describe numerical convergence, not runtime
performance.

## Citation and licenses

- Benjamin Wilfong, Anand Radhakrishnan, Henry A. Le Berre, Steve Abbott,
  Reuben D. Budiardja, Spencer H. Bryngelson, “OpenACC Offloading of the MFC
  Compressible Multiphase Flow Solver on AMD and NVIDIA GPUs,” SC Workshops
  2024, [DOI 10.1109/SCW63240.2024.00242](https://doi.org/10.1109/SCW63240.2024.00242).
- Anand Radhakrishnan et al., “Method for portable, scalable, and performant
  GPU-accelerated simulation of multiphase compressible flow,” *Computer
  Physics Communications* 302 (2024), 109238,
  [DOI 10.1016/j.cpc.2024.109238](https://doi.org/10.1016/j.cpc.2024.109238).
- MFC source and derived numerical results: MIT, copyright Spencer Bryngelson
  and Tim Colonius (2021).
- Adapted exact reference: MIT, copyright Jerko Skific (2015).
- Silo: LLNL three-clause BSD license.

The applicable notices are copied into the image and every result workspace.

## Limitations

Only one one-dimensional ideal-gas validation case is tested. The exact
reference uses deterministic quadrature of an analytic Riemann solution and
does not establish general MFC accuracy. CPU timings depend on the host and
must not be presented as accelerator evidence. Publication and anonymous Hub
verification remain separate gates after a validated daemon run.
