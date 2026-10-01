# AI Video Studio

An offline, CPU-compatible video production pipeline. A short creative brief is
expanded into a storyboard, deterministic illustrated frames, narration audio,
and a final MP4. The fixture deliberately avoids hosted APIs: it uses Python for
planning and raster generation and FFmpeg for encoding.

## Pipeline

`brief -> storyboard -> scenes -> narration -> compose -> quality-control`

Run `./run.sh`. FFmpeg produces the final MP4 when available and the container
image installs it. Minimal CI workers use a standards-compliant YUV4MPEG video
as the deterministic offline smoke artifact.
Set `AKOFLOW_PROFILE=demo` (default: `smoke`) for more frames and a longer video.
The versioned brief in `data/brief.json` is the complete offline dataset.

The stages map directly to AkôFlow activities. Their files are written to the
shared workspace, so provenance can show which activity generated each asset.
