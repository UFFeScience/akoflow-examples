# Common and independent dynamic time warping

This synthetic benchmark isolates temporal alignment choices, inspired by
the [SBBD study by Torres and colleagues](https://sol.sbc.org.br/index.php/sbbd/article/download/30740/30543/).
Two Gaussian event channels share one path in the common strategy. The
independent strategy allows one path per channel, using the same squared
error, endpoints, and allowed steps.

The 256-case design crosses 16 seeds, eight lag levels and both strategies.
Controls cover identical sequences and equal shifts of both channels.
