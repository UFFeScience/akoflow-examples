# Microscopy video stabilization

This synthetic experiment measures how anchoring frames to the first
observation and composing consecutive alignments affect trajectory drift.
It is motivated by preprocessing in Freire, Silva, Bernardes, Tavares,
Mello and Ferrari's [intravital microscopy study](https://sol.sbc.org.br/index.php/sbcas/article/download/29123/28928/).
It uses generated imagery and studies global translation under moving
foreground objects, without using imagery from the study.

The manifest crosses 64 seeds, four translation amplitudes and three
noise/foreground regimes. Each of the 768 independent cases generates
40 frames by cropping observations of a larger field. The trajectories
compare cross-correlation and phase correlation, with direct and composed
alignment, against an unregistered control. The ambiguity check evaluates
normalized spatial correlation over a fixed central tile. Ground truth
enters only the scoring step. The reported vector aligns a moving frame to
the reference and consequently has the opposite sign to the scene motion.

A local kernel check uses Python with NumPy 2.5.5.

```sh
python3 stabilize.py 0 sequence.csv
```

The CSV contains one row per frame and method, retaining explicit
ambiguity and unavailable states. Each frame records mean absolute intensity
error and pixel count for the intersection of valid bilinear footprints
across available methods, including the unregistered control. This entry
point checks the numerical
kernel locally. The AkôFlow execution, aggregate figures and publication
evidence are pending.

## Local visual pilot

Case 11 uses seed 532, a 6 px amplitude, and the strongest synthetic
noise/foreground regime. The final-frame plot and 40-frame animation compare
the observed image with both phase-correlation trajectories. Their lower
panels show absolute residuals against the first frame. Image intensities
use a fixed −3 to +3 range and residuals use a fixed 0 to 3 range. Black
pixels at the alignment boundary indicate missing values. The panel labels
report error on the shared valid pixels.

![Final-frame alignment and residuals for case 11](evidence/stabilization-residuals.png)

![Forty observed and stabilized frames with their residuals](evidence/stabilization.gif)

[Download case 11's per-frame pilot measurements](evidence/pilot-sequence.csv).
