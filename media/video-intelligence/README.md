# Video Intelligence

An offline media-understanding workflow with a reproducible generated dataset.
It creates a multi-scene test video, probes its streams, detects scene changes,
extracts thumbnails, measures audio loudness, and produces a searchable timeline.
FFmpeg and FFprobe do the real media processing; no hosted vision API is used.
Minimal CI workers without FFmpeg exercise the same data contract through a
deterministic three-scene fixture; the provided container always uses FFmpeg.

Run `./run.sh`. The `prepare` activity generates `outputs/source.mp4`, making the
dataset reproducible on any machine with FFmpeg. Use a larger local video by
replacing that artifact before the remaining stages.
