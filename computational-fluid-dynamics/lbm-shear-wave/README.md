# Periodic shear-wave decay with lattice Boltzmann

A synthetic single-phase check of a D2Q9 BGK method, inspired by the
[SSCAD 2024 study](https://sol.sbc.org.br/index.php/sscad/article/view/31001) by
Thiago Teixeira, Frederico L. Cabral, Micaella Coelho, Luciano Leite, Rodrigo
Surmas, Marcio Borges and Carla Osthoff (LNCC, COPPE and CENPES). The
[linear dispersion model](https://doi.org/10.1103/PhysRevE.61.6546) is due to
Pierre Lallemand and Li-Shi Luo. The code and constructed inputs use the
[MIT license](LICENSE).

The periodic grid has eight streamwise nodes and eight possible transverse
sizes. The 1,024 cases cross size, relaxation time, initial wavenumber and
amplitude. Each case estimates the decay rate from steps 32 through the
declared endpoint, compares it with both the viscous continuum rate and an
independent three-group Fourier reference, and checks density and momentum.
Case 1024 is the equilibrium control.

```sh
g++ -std=c++20 -O2 -fopenmp -Wall -Wextra -Werror src/shear_wave.cpp -o shear-wave
OMP_NUM_THREADS=1 ./shear-wave 127 results
```

The local [thread-equivalence test](evidence/thread-equivalence.csv) verified
eight corner cases and the equilibrium control. Each trace and summary was
byte-identical for one and two OpenMP threads. This records equivalence of
the local kernel; the AkôFlow scheduling benchmark and Hub publication are
pending.
