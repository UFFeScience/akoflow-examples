# PyCBC / LIGO — Gravitational-Wave Matched Filtering

Native AkôFlow gravitational-wave analysis using PyCBC 2.10.0 scientific functions, with complete real 4096-second H1/L1 GWOSC observations associated with GW150914. All 33,554,432 original 4096Hz strain samples are acquired and retained; no observed strain or software injections are simulated. Theoretical IMRPhenomD waveforms are used as matched-filter templates, not added to the observations.

Nine activities acquire observations, construct a 66-template physical mass grid, condition each detector, filter both detectors, evaluate zero-lag/time-shift coincidences, create scientific views and retain final artifacts. The mass grid covers component masses 20..70 solar masses in steps of five, with mass1 >= mass2 and zero spins. It is sparse and non-exhaustive, without a minimal-match guarantee. This is a targeted known-event reanalysis, not a full PyCBC HTCondor survey, calibrated false-alarm claim or parameter posterior.

The original data are highpassed at 15Hz, antialias-resampled to 1024Hz for the declared 20–300Hz filtering band and cropped by two seconds per edge. Median Welch PSD estimates use four-second windows/two-second stride with four-second Hann inverse-spectrum truncation. Full conditioned records are filtered; eight seconds per edge are excluded for wraparound. DATA/CBC_CAT1/CBC_CAT2 and NO_CBC_HW_INJ are required. Other original injection flags are preserved, including the L1 NO_CW_HW_INJ state; no claim that all kinds of hardware injections are absent is made.

Triggers above SNR 5.5 are clustered per template at 0.1s; shared-template H1/L1 pairs use a 15ms window and are clustered across templates at 1s. Fourteen declared time shifts provide exploratory score comparisons with a catalogue +/-1s exclusion. Followup chooses the strongest coincidence in the explicit known-event +/-0.5s window, or the global maximum if absent. No chi-square reweighting, calibrated significance or blind discovery is claimed. Detector strain, noise spectra, actual matched-filter SNR and coincidence plots are derived from measured arrays.

Run ./prepare.sh, ./validate.sh -definition, ./run.sh and ./validate.sh. Only acquisition needs network after preparation. Independent validation re-reads all raw observations, reproduces conditioning/PSD/selected filtering, checks the matched-filter normalization independently in the frequency domain, validates bank/trigger/coincidence invariants, verifies every derived hash and both PNGs. Upstream source/license are retained for provenance; the image uses the pinned installed PyCBC distribution and exact frozen dependency list. A contract check does not establish actual native completion.

Sources: https://github.com/gwastro/pycbc/tree/58f97dfcbeb9fe989fd7e42fd50b989311827ecd ; https://pycbc.org/pycbc/latest/html/gw150914.html ; https://gwosc.org/eventapi/json/GWTC-1-confident/GW150914/v3/ .

## Verified production publication

[Open PyCBC / LIGO on the production Hub](https://hub.akoflow.com/o/akoflow/scientific-workflows-pycbc). Native execution completed **9/9 activities in 161.948 seconds**, processing all 33,554,432 original H1/L1 strain samples and 66 physical templates. Independent matched-filter normalization, original data/result hashes, public image pull and both actual dark-theme figure views passed.

![Actual detector analysis](https://hub.akoflow.com/showcase-results/scientific/pycbc/published-detector-analysis.png)

![Actual coincidence analysis](https://hub.akoflow.com/showcase-results/scientific/pycbc/published-coincidence-analysis.png)

Exact executed image, transferred without rebuilding:

```text
hub.akoflow.com/akoflow-examples/pycbc@sha256:43c41477e1dd556ab921f1832b3f638e60f49dd3f1b25d2a214f61308027227a
```

Native capture, scientific checks and all public download hashes are recorded in `evidence/daemon-run.json`, `evidence/scientific-validation.json` and `evidence/production-acceptance.json`.
