# Grid random walks for particle dispersion

This synthetic adaptation is inspired by the thermal dispersion workload
in the [WSCAD-SSC study by André L. de Oliveira, Inês Dutra, Alexandre
Plastino and Simone de L. Martins](https://sol.sbc.org.br/index.php/sscad/article/download/17388/17224/).
The experiment tests count conservation and analytic moments under a
homogeneous lattice walk.

Four step distributions each use 64 independent batches of 256 particles.
The reference has 80 steps and the longer workload has 320. Batch seeds
are fixed by scenario and index. Validation checks endpoints, lattice
parity, total counts, repeatability and reduction order. The mean uses
a six-standard-error tolerance. Each covariance entry uses 6% of the
product of the corresponding theoretical marginal standard deviations.
