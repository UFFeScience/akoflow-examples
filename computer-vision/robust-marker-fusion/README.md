# Robust marker fusion on synthetic trajectories

Inspired by the multimarker visualization in the [TrATAR paper by Paiva and Queiroz at UFAL](https://doi.org/10.5753/sbie.2022.224883),
this geometry experiment compares a mean and a coordinatewise median
under partial occlusion and biased observations. The input is generated
without using recordings or patient data.

Sixteen synthetic trajectories cross four occlusion levels and four biases.
Each comparison uses the same visibility mask, noise and known orientation.
Transforming the known marker offsets into the observation frame yields
candidate centers. Frames with no visible markers have no estimate.
