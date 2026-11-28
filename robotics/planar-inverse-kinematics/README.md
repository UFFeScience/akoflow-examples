# Planar inverse kinematics and branch continuity

This geometric experiment is inspired by the [ERI-GO study by Zacca and colleagues at PUC Goiás and UFG](https://sol.sbc.org.br/index.php/erigo/article/download/13859/13706/).
It uses synthetic targets and a two-link planar arm. The shoulder angle
is measured counterclockwise from the x-axis, and the elbow angle is
relative to the first link. Angles are radians and links are 1.0 and 0.7
simulation units.

The 256-frame reference includes two reach-boundary controls with one
pose and two unreachable controls. Dynamic programming minimizes the
sum of squared circular changes across contiguous reachable frames.

## Run in AkôFlow

Register the pinned recipe, generate the default 256-frame workflow,
then execute preflight.

```sh
recipe=$(./register-recipe.sh)
python3 generate.py "$recipe"
./run.sh
```

Run `python3 profile.py /path/to/evidence` with the target daemon's
`AKOFLOW_API_URL` and `AKOFLOW_API_TOKEN`. It measures four slot counts,
checks all 259 deterministic outputs, and records the aggregate's
preparation and execution times. A second trajectory is available with
`--trajectory 1` in separate generated plans.

The original workflow code is released under the [MIT license](LICENSE).
