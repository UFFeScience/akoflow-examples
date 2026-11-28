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
The 1,033-activity AkôFlow DAG uses eight sample-preparation tasks, 1,024
prediction tasks and one aggregation. Each prediction receives the prepared
sites for its own surface. The [portable build recipe](evidence/portable-recipe.json)
records the build context and recipe digests. The 732-byte context fetches the
manifest and scripts from the immutable `e95a6b1` revision during the image build.
Each fetch has an enforced SHA-256. Activities need no external data access.
All 1,033 executable checks
passed preflight on an isolated daemon supporting shared recipe probes.
Measured scheduling profiles and the Hub run are pending.

To register the recipe, regenerate the plans and perform a preflight:

```sh
recipe=$(./register-recipe.sh)
python3 generate.py "$recipe"
./run.sh
```

The generated plans cover 1, 4, 8, 16 and 32 logical slots. The default plan
uses four slots. Set `AKOFLOW_SUBMIT=1` to execute after preflight.

![Analytic surface, estimates and errors for synthetic surface 3](evidence/idw-comparison.png)

![Eight synthetic surfaces comparing raw and filtered IDW predictions](evidence/idw-surfaces.gif)

The animation shows the spatial estimates and errors across all eight surfaces.
The outlined strip is excluded from sample training in every frame.

[Held-out metrics](evidence/metrics.csv) ·
[Local pilot validation](evidence/validation.json)

Run the measured campaign on one daemon after registering the recipe and
generating the plans. The runner resumes existing runs by ID and validates the
1,024 block outputs and all four aggregate hashes before using a measurement.

```sh
python3 profile.py profile-evidence
python3 summarize-profiles.py profile-evidence profile-summary
```

The [compact recipe smoke test](evidence/portable-build-smoke.json) rebuilt the
image from its archived Dockerfile, verified the sample manifest, and ran a
prediction block with network access disabled. Its result matched the local
pilot byte for byte. The
[installed dependency list](evidence/portable-build-dependencies.txt) records
the environment used in the smoke test.
