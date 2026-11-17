# Orcasound — Hydrophone Audio and Orca Call Candidates

Run the real hydrophone-audio processing chain as twelve AkôFlow activities: verified acquisition, three branches each with conversion, spectrogram calculation and trained inference, prediction merging and scientific result assembly. The frozen profile uses twelve complete consecutive public HLS objects from Bush Point session `1539203407`, approximately two minutes of audio. It is a bounded observation profile, not a claim to process an entire day or the full archive.

## Scientific inputs and model

The recording URLs, object lengths, original MD5 ETags, SHA-256 digests and playlist durations are frozen in `data/input-verification.json`. Every TS object is decoded in full by FFmpeg. Per-file sample count, rate, channel count, RMS energy and WAV hash are measured from the actual decoded observations.

Inference uses the official OrcaHello ResNet50 SRKW detector and its actual trained safetensors checkpoint at immutable revision `f8705749f36d65d870cc7b5d21e71802ae77059e`. All 332 tensors must load strictly into the matching unmodified official implementation; no random or partially loaded model may yield a result. The official frontend/config are retained, including the declared three-second windows, two-second hop, normalization, model feature preparation and aggregation. Candidate scores require expert confirmation and do not establish that orcas are present.

The Pegasus repository's old VGGish/checkpoint-directory lookup does not load its supplied FastAI learner file. This adaptation declares the matching official trained implementation rather than reporting randomly initialized predictions as science. Original conversion, power-spectrogram, inference and merge purposes remain; numerical equivalence to that broken lookup is not claimed.

## Run

On Linux amd64 with Docker and Go:

```sh
./prepare.sh
./run.sh
```

The image contains pinned CPU PyTorch 2.9.1, torchvision 0.24.1, torchaudio 2.9.1 and the recorded scientific dependencies. Only the acquisition activity requires internet access; it retrieves the complete frozen observations and unmodified official inference payload and verifies every file. The standalone runner disables container networking for all other activities. Subsequent scientific computations use local inputs. The daemon profile requests two execution lanes on a four-CPU, 12-GiB allocation; measured execution must be inspected separately before a completed result is claimed.

The upstream [OrcaHello RAIL-AMS license](https://github.com/orcasound/aifororcas-livesystem/blob/dd879cfd4140c70e1478a2d67c41a13e0ee7acf4/InferenceSystem/model/LICENSE) prohibits redistribution of its artifacts. Consequently this source bundle and image contain our wrapper, scientific dependencies and hash manifests. Every installation retrieves the unmodified official source and weights directly for local use, retaining their license. That private payload is excluded from public source/image/result archives. Use remains subject to the upstream terms.

## Scientific visualizations and validation

The final activity owns `orcasound-results.tar.gz`, `orcasound-summary.json`, a contact sheet of twelve real power spectrograms (`hydrophone-spectrograms.png`) and a per-window trained-model confidence figure (`orca-confidence.svg`). The public result archive retains all twelve decoded WAV files, individual spectrograms and measured predictions. Its numeric results are generated from the real observations; no positive whale calls are fabricated.

Validation checks complete decoded duration against the source playlist, WAV integrity/energy, immutable source/model fingerprints, strict trained-tensor loading, all expected inference windows, thresholds and aggregation, actual PNG/SVG files, output hashes and exclusion of restricted model/source artifacts from public outputs. CI checks the large image and DAG contract; full native scientific execution and output validation are recorded separately. The completed native run and independent validation are recorded in `evidence/daemon-run.json` and `evidence/scientific-validation.json`.

Original workflow: [Pegasus Orcasound](https://github.com/pegasus-isi/orcasound-workflow/tree/c66d070663b02536ac730b4f32f3812fdeffa2f4). Trained inference: [official OrcaHello source](https://github.com/orcasound/aifororcas-livesystem/tree/dd879cfd4140c70e1478a2d67c41a13e0ee7acf4/InferenceSystem). Exact adaptation and provenance are in `data/upstream.json`.

## Verified production publication

[Open Orcasound on the production Hub](https://hub.akoflow.com/o/akoflow/scientific-workflows-orcasound). The measured Linux amd64 Docker run completed **12/12 activities** in **92.417 seconds**. It decoded **120 seconds** of real stereo hydrophone audio and scored **48 complete inference windows**, with **zero positive candidates** at the configured thresholds. This does not establish species absence.

![Real hydrophone spectrograms](https://hub.akoflow.com/showcase-results/scientific/orcasound/hydrophone-spectrograms.png)

![Actual trained-model window scores](https://hub.akoflow.com/showcase-results/scientific/orcasound/orca-confidence.svg)

The exact executed dependency/wrapper image is distributed without a rebuild at:

```text
hub.akoflow.com/akoflow-examples/orcasound@sha256:fdf5475451f0787c8b2c58e4ae0a1fdd798d8a00a8f2fd82d50d29edcfff1c98
```

The original local image identity is retained in the native capture. Full public download hashes, public Docker pull and actual dark-theme PNG/SVG rendering passed acceptance. The public source/image/results exclude the restricted model and upstream inference source; direct upstream acquisition remains part of each execution. See `evidence/production-acceptance.json`.
