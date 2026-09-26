# README asset provenance

These assets support the GitHub repository homepage. Artwork and synthetic
figures are not experimental evidence.

| Asset | Source and regeneration |
| --- | --- |
| `saxsabs-overview.png` | Conceptual cover illustration generated with the built-in OpenAI image-generation tool on 2026-09-26. The prompt is preserved in `overview-prompt.txt`. It contains no experimental data, measured values, or software screenshot. |
| `workflow.svg` | Generated from `paper/generate_figures.py` with `python paper/generate_figures.py --demo`; it is a package-workflow schematic with no measured data. |
| `kfactor-demo.png` | Synthetic calibration figure generated from `paper/generate_figures.py` with `python paper/generate_figures.py --demo`; it is not beamline validation. |
| `workbench.png` | Curated copy of `paper/fig_gui.png`, captured from the current source tree with `python paper/capture_gui_screenshot.py`. It shows the application interface and contains no measurement data. |
| `hero.svg` | Legacy hand-authored calibration-path diagram retained in this folder; it is no longer used as the root README cover. It contains no measured data. |

When a source figure is regenerated, update its README copy in the same change.
