# Kermack–McKendrick SIR threshold and final-size sweep

This CPU workflow reproduces a bounded mathematical result from W. O. Kermack and A. G. McKendrick, “A Contribution to the Mathematical Theory of Epidemics,” *Proceedings of the Royal Society A* 115 (1927), 700–721. It audits the normalized constant-rate SIR threshold, susceptible fraction at the infection peak, and implicit final-size relation. It is a numerical-method reproduction, not a model or forecast of a named disease.

Eight synthetic scenarios use `S(0)=0.999999`, `I(0)=0.000001`, `R(0)=0`, `gamma=1/7 day^-1`, and `R0` values 0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, and 5.0. Each independent branch runs SciPy DOP853 and Radau and compares them with the nontrivial analytic final-size root. The `R0=1` case is correctly subthreshold because `R0*S(0)<1`.

## Reproduce

```sh
./build.sh
./preflight.sh
./run.sh
AKOFLOW_SUBMIT=1 ./run.sh
```

The container is CPU-only, receives no data, runs with networking disabled during the local preflight, and contains no Docker socket or Hub credential. `plan.yaml` assigns the eight scientific branches over four slots. Only measured daemon activity timestamps establish overlap. No parallel speedup is claimed without a separately recorded matching one-slot daemon run.

## Validation

All trajectories must conserve `S+I+R` within `1e-10`, remain nonnegative within `1e-12`, preserve monotonic S/R behavior, reach the descending `I=5e-13` event, satisfy the analytic and numerical final-size residuals, and make both solvers agree in terminal S and peak I within `1e-8`. Superthreshold peak S must be within `1e-7` of `1/R0`. Fixtures cover the disease-free equilibrium, beta-zero removal, a short-time derivative, and gamma final-size invariance; gamma halving must double the numerically detected terminal-event time within `2e-4` relative ratio error. Two sequential preflights must produce byte-identical canonical JSON/CSV.

The gallery artifacts are `sir-threshold-final-size.png`, its SVG equivalent, a parameter-sweep GIF explicitly labeled as non-forecast, and a measured daemon timeline generated after execution.

The validated reference run is `community-sir-threshold-sweep-run-v2` using workflow version `community-sir-threshold-sweep-v2-v1` and image digest `sha256:903019bb4493ec6788b1a243c152682d620498f3a8bb026d9a797426883402b2`. It completed 12/12 activities in 17.766692 seconds. Four independent scenario integrations overlapped for 0.951750 seconds. This is concurrency evidence only; no speedup claim is made.

## Licenses and limitations

New workflow code is BSD-3-Clause. NumPy and SciPy are BSD-3-Clause, Matplotlib uses its PSF-compatible license, and Pillow uses HPND. The Python base image is pinned by digest. No paper figure, empirical data, patient record, or fitted parameter is redistributed.

This is the homogeneous, deterministic, closed-population constant-rate slice—not the paper’s full infection-age theory. It ignores demographics, heterogeneity, intervention, uncertainty, and parameter inference. The one-week removal scale is a controlled numerical parameter, not an estimate about people.
