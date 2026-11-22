# Sparse multiband RR Lyrae period recovery

This CPU-only workflow reproduces the bounded scientific claim in the lower
panels of Figure 5 of VanderPlas and Ivezić (2015): a shared-phase multiband
Lomb–Scargle model recovers the period of a sparse RR Lyrae light curve even
when the five twelve-sample single-band periodograms peak elsewhere.

The workflow is a paper slice, not a reproduction of the population-level
Stripe 82 or LSST accuracy experiments. Its input is a simulated light curve
derived from the empirical Sesar et al. (2010) templates, not a new stellar
observation.

## Fixed scenario and validation

- Template object: `1019544`; deterministic random seed: `0`.
- 60 nights selected from a 180-day season, alternating `ugriz` filters (12
  samples per band).
- 1,000 trial periods from 0.2 through 0.9 day.
- Shared model: `Nterms_base=1`, `Nterms_band=0`.
- Template period: `0.6224468350410461` day.
- Qualified grid maximum: `0.6225225225225225` day.
- Pass tolerance: absolute period error at most `0.001` day.

The validator also requires finite arrays, positive uncertainties, exact sample
counts, the qualified grid peak, a scientific PNG, and a scan GIF. It records
per-band maxima without inventing a numeric threshold for the paper's
qualitative single-band comparison.

## Scientific DAG

`prepare-observations` emits the derived 60-row input. Six independent
scientific branches then calculate the `u`, `g`, `r`, `i`, `z`, and shared
multiband periodograms. `aggregate-results` renders the comparison and folded
light curve while `animate-scan` visualizes the actual shared-period scan.
`validate` joins both branches and enforces the frozen criteria.

The periodogram fan-out is the parallel scientific work. Parallel execution
must be demonstrated from daemon-recorded activity timestamps. No speedup is
claimed unless a separate matching one-slot run is recorded.

## Reproducible build and preflight

The Dockerfile pins Python 3.11 (Bookworm), NumPy 1.26.4, SciPy 1.13.1,
astroML 1.0.2.post1, and gatspy revision
`71384b8d15531bc01a6b85250a35cd675edccf44`. Build is the only networked step:
it retrieves the upstream archives and freezes the derived observations inside
the image. Scientific activities run with `--network none`, one numerical
thread, no credentials, and no host Docker socket.

```sh
docker build -f docker/Dockerfile -t akoflow/community-rrlyrae-period-recovery:v1 .
./preflight.sh
# With the AkôFlow daemon available on port 8080:
./run.sh
```

After build, record the immutable image value with
`docker image inspect --format '{{index .RepoDigests 0}}'` for a pushed image,
or the local image ID before daemon execution. The AkôFlow definition is
`workflow.yaml`; infrastructure records are `environment.yaml`, `scope.yaml`,
and `topology.yaml`.

## Results

The local reference execution `community-rrlyrae-run-v5` completed all 10
activities through the AkôFlow daemon using workflow version
`community-rrlyrae-period-recovery-v1` and schedule plan
`community-rrlyrae-plan-v2`. The measured makespan was 13.201 seconds, with
13.682 compute-seconds and 822,447 transferred bytes at zero configured cost.

All six periodogram activities overlapped between Unix timestamps
`1795317712.354776` and `1795317712.580411` (0.226 seconds of six-way overlap).
The multiband result recovered `0.6225225225225225` day versus the template
period `0.6224468350410461` day, an absolute error of
`0.00007568748147634974` day within the `0.001`-day tolerance. The validator
passed every scientific and artifact check.

The local image ID was
`sha256:7e9428b67978842d772d2cdaa105328f69389d585b3370f26c48dc58f63789c3`.
Representative deterministic checksums are
`6cab4b4b655dab52b281de2d4fa684d994c23926dbe48e63e03615ae47fa9197`
for `observations.csv`,
`50fe12eb02b7145c9fa453ac0670fbc31bbbc0f8345f4e9888594385e5cca8ca`
for the multiband periodogram, and
`95cdb718599bbd385828cb5224174b7710f47c60fe5b0d0e3197cd4ffd9322b5`
for `validation.json`.

Hub publication and anonymous public verification remain separate release
gates; these measurements describe the local daemon execution only.

## Provenance, citation, and licenses

- Jacob T. VanderPlas and Željko Ivezić, “Periodograms for Multiband
  Astronomical Time Series,” *The Astrophysical Journal* 812(1), 18 (2015),
  [DOI 10.1088/0004-637X/812/1/18](https://doi.org/10.1088/0004-637X/812/1/18).
- Upstream paper scripts: `jakevdp/multiband_LS` revision
  `75aba85c3c7d47643deeabcfb15a6214cd086d61`, BSD-3-Clause.
- gatspy revision `71384b8d15531bc01a6b85250a35cd675edccf44`,
  BSD-3-Clause.
- Sesar et al. (2010) RR Lyrae data/templates, with catalog record
  [VizieR DOI 10.26093/cds/vizier.17080717](https://doi.org/10.26093/cds/vizier.17080717).

The original Sesar archives and template files are not published in the source
or results bundle. Their names, byte sizes, and SHA-256 values are captured in
`input-provenance.json`; only the minimal derived observation table is promoted
to offline execution.

## Limitations

Survey-window aliases are scientifically meaningful and are not treated as
software errors. Modern numerical libraries may differ from the 2015 stack;
the validator therefore checks the pre-qualified modern stack and records exact
arrays. The animation scans trial period; it is not temporal evolution of the
star. This workflow makes no population-level accuracy or parallel speedup
claim.
