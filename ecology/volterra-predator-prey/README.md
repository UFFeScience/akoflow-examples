# Volterra predator–prey invariant and cycle ensemble

This CPU workflow reproduces the first law in Vito Volterra's 1926 two-species model: prey and predator populations follow periodic cycles with a shared period and different phases. Three initial conditions are solved independently, then checked against the analytic first integral and combined into a phase portrait and trajectory animation.

## Scientific reference and scope

Vito Volterra, “Fluctuations in the Abundance of a Species considered Mathematically,” *Nature* 118, 558–560 (1926), [doi:10.1038/118558a0](https://doi.org/10.1038/118558a0).

The workflow reproduces only the paper's first law for the classical equations `dx/dt=αx−βxy` and `dy/dt=δxy−γy`. It does not fit observations or reproduce Volterra's fishing-intensity result. The implementation is original Apache-2.0 code; it bundles no paper, upstream source, or external data.

## Fixed scenario and validation

Coefficients are `α=1.1`, `β=0.4`, `δ=0.1`, `γ=0.4`, with equilibrium `(4, 2.75)`. DOP853 integrates `(10,5)`, `(15,3)`, and `(5,8)` on `[0,100]` using `rtol=1e-11`, `atol=1e-13`, and `max_step=0.05`. Validation requires positive finite populations, seven stable event-refined cycles, nonzero phase offsets, winding/cycle agreement, reference period agreement, and relative drift at most `1e-9` in `H=δx−γ ln(x)+βy−α ln(y)`.

The recorded run passed. Mean periods were 10.7888777282, 11.0717506922, and 12.1051471690 model-time units. Maximum relative invariant drift across scenarios was `7.51e-14`. These results describe the idealized deterministic model, not real ecological forecasts; neutral cycles are structurally fragile and the model omits carrying capacity, stochasticity, delays, space, and response saturation.

## Workflow and reproducibility

`prepare` fans out to three independent scientific solves on separate Docker resources, followed by aggregation, rendering, and validation. Build with `./build.sh`, run the isolated deterministic double preflight with `./preflight.sh`, and use `./run.sh` for daemon preflight (`AKOFLOW_SUBMIT=1 ./run.sh` submits idempotently).

The image is pinned from `python:3.11.14-slim-bookworm` and recorded locally as `sha256:eb21fc18249d95b8aa1de6dc45886c9ff6f67bbe1d8b67d26ffc94e0c2cf8241`. Scientific execution uses no network, credentials, or host Docker socket.

## Recorded daemon evidence

- run: `community-volterra-predator-prey-run-v1`
- workflow: `community-volterra-predator-prey-v1-v1`
- plan: `community-volterra-predator-prey-plan-v1`
- environment: `Community Volterra parallel local Docker`
- status: completed, 7/7 activities
- makespan: 28.358399 s; compute: 23.543672 s; transferred: 12,816,245 bytes; configured cost: 0
- three-way solve overlap: 1.447831 s, from `1795370418.1838381` to `1795370419.631669`

This is measured concurrency evidence, not a speedup claim; no matching one-slot run was performed. The timeline is in `evidence/measured-timeline.png`, with exact timestamps in `evidence/measured-activities.json`.

Key validated hashes are `ensemble-metrics.csv` `7a7e0635...9ecb`, `ensemble-metrics.json` `9a8cfcfd...249a`, `population-cycles.png` `7ff02ffe...83f1`, `predator-prey-cycles.gif` `d6c32100...715a`, and daemon `validation.json` `a59e3cc6...61d59`.

Hub publication and anonymous public verification are deliberately not claimed here. They remain gated on a daemon connection to Community Explorer project `44e9e6b5-454b-43b9-bf73-240be5e31aab`.
