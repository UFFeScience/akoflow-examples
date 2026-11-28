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

## Local pilot artifacts

The panels compare the high-resolution truth and three treatments for
seed 0 at 2× reduction. The upper row uses a fixed reflectance scale.
The lower row shows centroid classification, with green for a correct
target pixel, orange for a false positive, and purple for a false
negative. Labels report target IoU and edge RMSE. The animation holds the
scene and resolution fixed and varies PAN interference across the three
registered levels.

![Fusion and classification maps for the low-interference control](evidence/pansharpening-classification.png)

![Three levels of PAN interference on the same scene](evidence/pan-interference-sweep.gif)

[Download pilot metrics for all three treatments and 768 scenes](evidence/pilot-metrics.csv).
