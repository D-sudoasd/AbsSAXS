# Minimal anonymized 2D reproducibility package

This folder provides a reviewer-friendly deterministic dataset and script for a
synthetic raw-frame validation without proprietary beamline files.
The expected standard and sample curves are defined before reduction; the
reference is not calculated from the measured profile.

## Files

- `synthetic_detector_image.csv`: anonymized 9x9 detector shape template
- `synthetic_geometry.json`: minimal geometry metadata
- `run_minimal_2d_pipeline.py`: deterministic 2D→1D→K-factor→absolute export

## Run

```bash
python examples/minimal_2d/run_minimal_2d_pipeline.py
```

Output directory: `examples/minimal_2d/outputs/`

Expected key result:

- `summary.json` with `k_relative_error < 0.005` and
  `sample_max_relative_error < 0.01`
- `absolute_profile.csv`, `absolute_profile.tsv`, `absolute_profile.xml`
- `absolute_profile.h5` if `h5py` is installed (`pip install -e ".[hdf5]"`)

The example recovers a planted synthetic $K$ and sample curve on a 9×9 array
using a homemade integer-bin radial average (not pyFAI), writes labeled
`absolute_cm^-1` outputs with unknown uncertainty, and checks that the XML
exposes `i_abs` rather than `i_rel`. It uses `build_nist_net_image` for
detector-space blank subtraction; it does not run the BL19B2 campaign runner,
pyFAI integration, a measured SRM 3600 coupon, or a third-party format consumer.
