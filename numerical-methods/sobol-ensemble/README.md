# Scrambled Sobol and pseudorandom integration

This workflow compares convergence of two randomized integration methods on
two 16-dimensional functions whose integrals are known exactly. It also
measures how the same 128 independent replicates execute across AkôFlow slots.

## Paper and authors

Zexin Pan and Art B. Owen, *The nonzero gain coefficients of Sobol's
sequences are always powers of two*. The synthetic experiment explores
empirical convergence using SciPy's documented linear matrix scramble and
digital shift. The AkôFlow implementation is by the Community Explorer.
[Paper](https://artowen.su.domains/reports/gainpow2.pdf)
[SciPy Sobol documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html)

## Scenario and workflow

The smooth integrand is the product of `1+xⱼ` across 16 coordinates. Its
integral is `(3/2)^16`. The discontinuous integrand indicates whether the
coordinate sum exceeds eight. Its integral is one half by symmetry.
Each method and integrand pair has 32 independent replicates. A fixed
NumPy SeedSequence with entropy 107 creates all 128 distinct seeds.

The preparation activity verifies independent streams, nested prefix
generation, a constant-function fixture, and the indicator boundary. A
replicate generates up to 2²⁰ points, reporting estimates at 11 power-of-two
prefixes. Scrambled Sobol replicates are initialized independently and each
uses one balanced stream. The pseudorandom control uses the same sample
counts. The image pins NumPy 2.4.2 and SciPy 1.17.1.

The aggregation activity verifies the manifest and collects all 1,408
estimates. The CSV reports signed error by replicate and the summary
reports empirical RMSE, bias, sample variance, and the standard error of
the ensemble mean. Prefixes are nested, so their errors are correlated.

## Run

The portable build carries the scripts and a digest-pinned Python base image.
For a local image and the four-slot reference execution:

```sh
docker build -f docker/Dockerfile -t community-sobol-ensemble:v1 .
./run.sh
AKOFLOW_SUBMIT=1 ./run.sh
```

To run three repetitions of each 1-, 4-, 8-, and 16-slot profile sequentially
and verify identical output digests:

```sh
python3 profile.py profile-evidence
python3 summarize-profiles.py profile-evidence profile-results
```

The profiling driver resumes existing execution IDs and waits for each run
before starting the next. The summary reports both end-to-end time and
time after preparation. The latter comparison excludes the initial image
build. With eight host CPUs, 16 logical slots can compete for the same
cores. Replicate process timings and peak RSS are exported separately
from daemon activity timings.

## Outputs and limitations

The workflow emits per-replicate estimates, convergence summaries, replicate
timings, a convergence figure, an animation, and validation checksums.
The empirical comparison concerns these functions and seeds. The experiment
measures convergence and scheduling on these fixed test cases.

## Four-slot reference run

Run `community-sobol-run-4-v1` completed all 130 activities and validated
1,408 estimates. The daemon recorded a peak of four simultaneous replicas.
At 2²⁰ points per replica, the observed RMSEs were 0.005285 for Sobol and
0.429079 for pseudorandom sampling on the smooth function. On the indicator,
the observed RMSEs were 0.000177 and 0.000600 respectively.

![Empirical RMSE across nested sample counts](outputs/convergence.png)

![Convergence at the eleven prefix lengths](outputs/convergence.gif)

![Measured concurrent replicas in the four-slot run](outputs/timeline.png)

[Replicate estimates](outputs/replicates.csv) ·
[Convergence summary](outputs/convergence.csv) ·
[Process timing and peak RSS](outputs/replicate-timing.csv) ·
[Validator](evidence/validation.json) ·
[Recorded activities](evidence/reference-run.json)
