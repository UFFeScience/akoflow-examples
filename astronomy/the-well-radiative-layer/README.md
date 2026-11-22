# The Well radiative mixing-layer phase-transfer audit

This CPU workflow audits the nine official test trajectories in The Well
`turbulent_radiative_layer_2D` dataset, one trajectory for each cooling time.
It measures density-weighted cold, intermediate, and hot phase fractions from
`T = pressure / density`, RMS speed, and discrete-mass drift. It is a bounded
2D dataset adaptation, not a reproduction of the associated paper's 3D
scaling experiment and not a seed-ensemble uncertainty estimate.

## Frozen result and acceptance

The dataset is pinned at revision
`2ee7756575ff6f90981d0308cbcb6a2ab5995bdc`. The initial equilibrium
temperatures are 0.01 and 1.0. Log-space thirds fix phase boundaries at
0.04641588833612779 and 0.21544346900318834. The late window is the final 21
of 101 stored frames. The validator requires every late cold-fraction change
to match the qualified float64 reference within `1e-10`, phase closure within
`1e-12`, all pinned object hashes, and the sign transition between cooling
times 0.32 and 0.56.

The pinned repository contains 27 files and 72 trajectories: six train, one
validation, and one test trajectory at each of nine cooling times. This
conflicts with the upstream README's 90-trajectory statement and is reported
rather than silently reconciled.

## Isolation and execution

`prepare-inputs.sh` is the separately declared input-preparation step. It
copies only the nine checksum-verified test objects from a cache into the
ignored Docker build context. `build.sh` is the only dependency/image step
that may use network access. Scientific containers run with `--network none`,
without credentials and without the host Docker socket.

```sh
./build.sh
./preflight.sh
./run.sh
```

The AkôFlow DAG has one `prepare` activity, nine scientifically independent
cooling-time analyses, then `aggregate`, `render`, and `validate`. The
four-slot daemon run must show timestamp overlap between independent analyses.
A matching one-slot run is required before making any speedup claim.

## Outputs

Each branch emits all 101 per-frame phase fractions and diagnostics plus a
summary. Aggregation emits CSV and JSON results. Rendering creates a cooling
time result figure, phase-evolution figure, and GIF from the actual reference
records. Validation records deterministic artifact SHA-256 values. Daemon run
IDs, image identity, measured timing, timeline/DAG evidence, and limitations
are added only after the recorded runs complete.

## Citation, attribution, and licenses

- Ruben Ohana et al., “The Well: a Large-Scale Collection of Diverse Physics
  Simulations for Machine Learning,” NeurIPS 2024 Datasets and Benchmarks,
  DOI `10.52202/079017-1430`.
- Drummond B. Fielding, Eve C. Ostriker, Greg L. Bryan, and Adam S. Jermyn,
  “Multiphase Gas and the Fractal Nature of Radiative Turbulent Mixing
  Layers,” *ApJL* 894 L24 (2020), DOI `10.3847/2041-8213/ab8d2c`.
- Dataset metadata: CC BY 4.0. The Well code/schema revision
  `aac88c0b5eb9cbe4b7b2797eaaa550a43706fb44`: BSD-3-Clause.

The HDF5 objects are inputs and are not committed to this repository.

## Limitations

There is one test trajectory per cooling time, so no confidence interval or
seed variance is claimed. Fractions use a discrete density sum because cell
edge conventions are not explicit. The open y boundary makes mass drift a
diagnostic rather than an assumed conservation failure. No power-law exponent
or parallel speedup is an acceptance target.
