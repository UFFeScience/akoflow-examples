# Synthetic inverse-distance interpolation audit

This original synthetic study is motivated by Gustavo E. Kida and Raul T. Santos
(UFMT) and their [SBIAGRO 2021 study of interpolation workflows](https://doi.org/10.5753/SBIAGRO.2021.18398).
The experiment uses eight analytic surfaces, dispersed and clustered samples,
IDW exponents 2 and 4, and a common held-out strip. All training inputs are
generated here, with no paper datasets or figures copied.

The frozen inputs are [samples.json](evidence/samples.json) with
[SHA-256](evidence/samples.sha256). Training-only leave-one-site-out residuals
determine the filter prior to prediction. Exact duplicate coordinates are
averaged and their original IDs preserved. Each of the 32 prediction cases
has 32 disjoint blocks. The aggregate applies a scalar inverse-distance
formula independently and checks every cell within an absolute tolerance of
1e-12. MAE and RMSE use the spatial region excluded from training.

The local pilot verified all 1,024 blocks and 32 assembled grids. The filter
identified all 20 synthetic spikes and also removed 27 other observations.
Holdout RMSE improved in six of sixteen paired surface/exponent comparisons.
The AkôFlow DAG, measured scheduling profiles and Hub run are pending.

![Analytic surface, estimates and errors for synthetic surface 3](evidence/idw-comparison.png)

[Eight-surface animation](evidence/idw-surfaces.gif) · [Held-out metrics](evidence/metrics.csv) ·
[Local pilot validation](evidence/validation.json)
