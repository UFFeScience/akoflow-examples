from parsl import python_app

from lib.tile_tasks import compute_cmd_masks_job as compute_cmd_masks
from lib.tile_tasks import run_gawa_tile_job as run_gawa_tile

compute_cmd_masks_job = python_app(compute_cmd_masks)
run_gawa_tile_job = python_app(run_gawa_tile)
