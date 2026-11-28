# Pansharpening and crop classification

This synthetic experiment is inspired by Bendini et al. at INPE,
[Effects of Image Fusion Methods on Sugarcane Classification with
Landsat-8 Imagery](https://www.esensing.org/papers/paper_104.pdf), SBSR 2015.
It studies how edge reconstruction and downstream classification can
change in different directions. The code and generated scenes use MIT.

The manifest crosses 64 disjoint test seeds, four resolution factors, and
three PAN interference levels. Eight separate seeds calibrate the
three-band class centroids for each treatment and condition. Each case
compares resampling, additive detail injection, and replacement of the
first principal component. It reports finite-difference edge error,
per-band spectral RMSE, and target IoU for a fixed rule and the calibrated
classifier.

```sh
python3 fusion.py calibrate centroids.json
python3 fusion.py case 0 centroids.json case-000.csv
```

The local numerical check reproduced the expected reversal in all 256
zero-interference cases. The AkôFlow DAG, visual artifacts, scheduling
measurements, and Hub publication remain pending.
