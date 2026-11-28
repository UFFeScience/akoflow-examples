# Tiled maximum-intensity and depth projection

This synthetic experiment isolates maximum-intensity projection, motivated
by the marker visualization in the [SBCAS paper by Borges, Guliato and Machado](https://sol.sbc.org.br/index.php/sbcas/article/download/27706/27516/).
It operates on generated geometric volumes in `(z, y, x)` order.

Each independent tile emits the maximum intensity and earliest global
depth for each column. The reducer selects the greater intensity and
breaks ties by smaller depth. It checks that each 3D tile appears once,
including tiles clipped by the volume boundary.

The numerical kernel was compared against whole-volume NumPy maximum and
argmax for 64 × 128 × 128, 61 × 123 × 115 and 1 × 17 × 9 volumes.
Shuffled and reversed tile order gave exact results, including repeated
maxima and negative background values. Missing and duplicated tile inputs
were rejected.
