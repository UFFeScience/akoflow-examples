# INPE DETER monthly Amazon alert audit

[Issue #326](https://github.com/UFFeScience/akoflow-community-explorer/issues/326)

The input is INPE's anonymous TerraBrasilis layer `deter-amz:deter_amz`.
The [layer metadata and access details](evidence/qualification-sources.json)
record the applied CC BY-SA 4.0 license. Credit INPE and TerraBrasilis,
described by [Assis et al. (2019)](https://doi.org/10.3390/ijgi8110513).

Each partition covers one observation month using a closed start date and an
open end date. The provider reuses some identifiers for distinct observations.
The content SHA-256 of the entire record distinguishes those observations.
Validate municipal codes by matching their first two digits to the reported UF.

Report the source's municipal area as recorded. A separate geometric diagnostic
uses polygon coordinates and flags degenerate rings. Keep flagged features in
the source counts. The summed areas represent alert records, so the same area
can contribute more than once when alerts overlap or recur. Annual PRODES rates
use a separate product and method.

The frozen snapshot covers January 2019 through December 2024. The
[manifest](snapshot/manifest.json) records the date bounds, capture time,
feature count, and SHA-256 for every monthly archive. The
[independent qualification](evidence/qualification.json) found 334,054 records
and no missing reported area. The
[reference table](evidence/reference-by-month-state-class.csv) contains the
expected counts and reported area by observation month, state, and class.

```sh
python3 tools/freeze.py snapshot
python3 tools/qualify.py snapshot qualification
```

Capture resumes from each archive whose bytes match its recorded SHA-256.
Qualification checks the partitions and independently aggregates the records
by observation month, state, and class with SQLite.
