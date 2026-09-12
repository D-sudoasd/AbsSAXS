# README asset provenance

These files support the GitHub repository homepage and are not experimental
evidence.

| Asset | Source and regeneration |
| --- | --- |
| `hero.svg` | Hand-authored SAXS calibration-path diagram (measured I(q), reference I(q), K, absolute export); it contains no measured data. |
| `workflow.svg` | Hand-authored entry-point map for CLI utilities, Workbench, strict BL19B2, and Python API, with shared-core and output labels; the adjacent README table is authoritative. |
| `workbench.png` | Curated copy of `paper/fig_gui.png`, captured from the current source tree with `python paper/capture_gui_screenshot.py`. |
| `kfactor-demo.png` | Curated copy of `paper/fig_kfactor_demo.png`, generated deterministically with `python paper/generate_figures.py --demo`; it is synthetic and not beamline validation. |

`workbench.png` is expected to match `paper/fig_gui.png`. `kfactor-demo.png` is
the approved README export of the generated synthetic figure and may be updated
from `paper/fig_kfactor_demo.png` after visual review. When either source is
regenerated, update its README copy in the same change and record both hashes.
