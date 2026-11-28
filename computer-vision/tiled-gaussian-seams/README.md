# Gaussian filtering across tile seams

The experiment takes inspiration from the Gaussian preprocessing in
[Oliveira and colleagues, SBCAS 2021](https://sol.sbc.org.br/index.php/sbcas/article/download/16057/15898/).
It uses eight synthetic images with diagonal edges, disks and impulses.
It studies convolution only and uses no clinical images or diagnostic tasks.

Four normalized kernels have explicitly fixed radii. A 4 by 4 grid assigns
each pixel to one core, including images whose dimensions are unevenly
divisible by four. Each of the 512 independent cases compares zero input
margin, one-third-radius margin and full-radius margin against the complete
image filtered with edge replication.
