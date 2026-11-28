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
