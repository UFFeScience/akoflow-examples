# Blender Render Farm

A frame-parallel 3D rendering workflow. Blender procedurally creates a scene,
two independent activities render disjoint frame shards, and FFmpeg assembles
the frames into an MP4 before a completeness check runs.

Run `./run.sh`. If Blender is installed it performs the real render. On small CI
workers, the script uses a deterministic CPU software-render fixture while the
provided container always installs and invokes Blender. Set
`AKOFLOW_REQUIRE_BLENDER=1` to reject that fixture. `AKOFLOW_PROFILE=demo`
renders 24 frames instead of the six-frame smoke profile.

