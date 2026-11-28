# Robust marker fusion on synthetic trajectories

Inspired by the multimarker visualization in the [TrATAR paper by Paiva and Queiroz at UFAL](https://doi.org/10.5753/sbie.2022.224883),
this geometry experiment compares a mean and a coordinatewise median
under partial occlusion and biased observations. The input is generated
without using recordings or patient data.

Sixteen synthetic trajectories cross four occlusion levels and four biases.
Each comparison uses the same visibility mask, noise and known orientation.
Transforming the known marker offsets into the observation frame yields
candidate centers. Frames with no visible markers have no estimate.

## Run in AkôFlow

Register the build recipe and generate the workflow and plans.

```sh
recipe=$(./register-recipe.sh)
python3 generate.py "$recipe"
./run.sh
```

Set `AKOFLOW_API_URL` and `AKOFLOW_API_TOKEN` for the target daemon.
Run `python3 profile.py /path/to/evidence` to execute or resume the 96-frame
reference and verify all 259 checksums across 1, 4, 16 and 32 configured
slots. Each capture records elapsed time, activity intervals, and peak
overlap based on valid intervals.

The optional `--frames 384` argument to `generate.py` creates a separate
long workflow with the same 256 scenarios. To submit it set
`AKOFLOW_WORKFLOW_ID=community-marker-fusion-long-v1` and `AKOFLOW_SUBMIT=1`
when running `./run.sh`.
