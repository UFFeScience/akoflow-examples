# SOMOSPIE soil-moisture inference

Scientific workflow adapted from TauferLab SOMOSPIE commit `55d317ea4d751d823086005dd5d8247e65dffd55`. The original BSD-3-Clause KNN/RF modeling functions and license are preserved unchanged in scripts/upstream. This publication describes the scientific workflow; execution environments are separate profiles.

## Real observation profile

A frozen Oklahoma crop [-99,35,-97,37], EPSG:4326, uses all 31 complete January 2010 ESA CCI COMBINED v07.1 daily global products and four complete Copernicus GLO-90 2021 surface tiles. The acquisition manifest records URLs, bytes and SHA256 for 35 objects (60,606,972 bytes). Acquisition downloads official sources directly; original source rasters are excluded from the public image, source package and derived results.

The workflow computes missing-aware monthly soil moisture on the native 0.25-degree grid, projects the surface to UTM14N at 90m for Horn slope/aspect and hillshade, and area-averages covariates onto observation/evaluation grids. The GLO-90 DSM includes vegetation and buildings, not bare-earth terrain. Its 2021 date differs explicitly from the 2010 moisture observations.

Unmodified upstream modeling routines perform a 10% holdout and full ten-fold searches: 50 KNN candidates (neighbors 2..19, original Gaussian/uniform/distance weights) and 10 random-forest candidates (original 300..2000 tree search). The adapter fixes split and RF estimator seeds to 3 and records actual CV results, scalers, indices and fitted models. Evaluation covers all 40,000 cells of a 0.01-degree grid. This geographic spacing is nominally about 1km and is not uniform metric resolution. Fine predictions are statistical inferences, not new independent observations. Seven held-out coarse cells cannot establish spatial or temporal generalization. Negative R2, if measured, is retained.

## Execution and visual results

Run `./prepare.sh`, `./validate.sh -definition`, then `./run.sh` and `./validate.sh`. Only acquisition requires outbound network. Twelve native activities produce georeferenced observed/predicted moisture maps and an actual held-out prediction diagnostic, plus derived tables, GeoTIFFs, trained models, full CV records and provenance. Publication of measured completion follows actual native execution and independent validation; a definition check alone does not demonstrate scientific completion.

## Sources and terms

- SOMOSPIE: https://github.com/TauferLab/SOMOSPIE
- ESA CCI v07.1 record: https://catalogue.ceda.ac.uk/uuid/c7e974411cfe4cf99cb077f7cb4d75d4/
- ESA scientific-use terms (no onward redistribution of original data): https://climate.esa.int/en/projects/soil-moisture/data/terms-and-conditions/
- ESA merging methodology: https://doi.org/10.5194/essd-11-717-2019
- Copernicus GLO-90, 2021 release: https://registry.opendata.aws/copernicus-dem/

Derived terrain products contain modified Copernicus DEM 2021 information. Original satellite products remain at their official providers. Public artifacts contain derived scientific results only. The obsolete original prepared-table Google Drive was unavailable; these tables are regenerated from real frozen observations, not synthetic data.

## Verified production publication

[Open SOMOSPIE on the production Hub](https://hub.akoflow.com/o/akoflow/scientific-workflows-somospie). The native run completed **12/12 activities in 127.084 seconds**, with independently verified full searches, 40,000 predictions per model and public download hashes.

![Observed and predicted soil moisture](https://hub.akoflow.com/showcase-results/scientific/somospie/published-soil-moisture-maps.png)

![Actual heldout errors](https://hub.akoflow.com/showcase-results/scientific/somospie/published-heldout-diagnostics.png)

The exact executed image is available without rebuilding:

```text
hub.akoflow.com/akoflow-examples/somospie@sha256:6b6efc494e7bfe24d2f83e0731b31e37e5a3141ef521acc38ad1f1bd1a430f31
```

See `evidence/daemon-run.json`, `evidence/scientific-validation.json` and `evidence/production-acceptance.json` for native capture, numerical checks, public image/download validation and dark-theme browser acceptance.
