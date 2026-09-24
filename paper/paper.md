---
title: 'saxsabs: Absolute-intensity calibration and provenance tracking for small-angle X-ray scattering'
tags:
  - Python
  - small-angle X-ray scattering
  - absolute intensity calibration
  - scientific software
  - synchrotron
authors:
  - name: Delun Gong
    orcid: 0000-0001-7877-7707
    email: dlgong@imr.ac.cn
    corresponding: true
    affiliation: '1'
affiliations:
  - index: 1
    name: Institute of Metal Research, Chinese Academy of Sciences, Shenyang 110016, China
date: 13 September 2026
bibliography: paper.bib
---

# Summary

`saxsabs` converts small-angle X-ray scattering (SAXS) data to an absolute
intensity scale through a Python library, command-line tools, batch workflows,
and a bilingual desktop interface. It normalizes monitor and transmission data,
estimates the reference-derived calibration factor $K$, records sample
thickness, detects previously applied corrections, propagates available
uncertainties, and exports text, canSAS, and NXcanSAS files. Built-in reference
curves cover NIST Standard Reference Material (SRM) 3600 glassy carbon
[@allen2017; @srm3600] and water at documented temperatures [@orthaber2000];
users can also supply reference curves.

The software stops operations when required physical metadata are missing or
inconsistent. Strict calibration records retain source hashes, units, physical
inputs, and applied corrections; other interfaces record the available source
identity and processing context. These records allow repeated or incompatible
processing to be detected. The source is distributed under the BSD-3-Clause
license, with archived releases linked through Zenodo [@saxsabs_archive].

# Statement of need

Absolute scaling enables quantitative comparison of SAXS measurements and their
interpretation as differential scattering cross sections
[@allen2017; @orthaber2000]. It requires consistent treatment of detector background,
exposure or monitor normalization, sample transmission, reference and sample
thicknesses, and the calibration standard. Beamline metadata and one-dimensional
(1D) profiles also vary in field names, units, and delimiters; undocumented
assumptions therefore hinder auditing.

`saxsabs` serves beamline scientists and SAXS users who need to convert external
1D profiles or detector images with compatible metadata and geometry to absolute
intensity while retaining processing records. The current strict 2D workflow is
implemented for BL19B2 data conventions. The software distinguishes `raw_counts`,
`relative`, `absolute_cm^-1`, and `ambiguous` states. Scaling and buffer
subtraction run only when the declared state and required metadata are compatible;
otherwise, the software identifies the missing or conflicting information.

# State of the field

pyFAI handles detector geometry and azimuthal integration [@pyfai], and FabIO
reads detector-image formats [@fabio]. Dioptas supports two-dimensional
diffraction reduction and exploration [@dioptas]. SasView and Irena provide
small-angle-scattering analysis and model fitting [@sasview; @irena], whereas
BioXTAS RAW combines BioSAXS reduction, water- or glassy-carbon scaling, buffer
subtraction, and subsequent analysis [@bioxtasraw].

`saxsabs` complements these packages by focusing on absolute-scale calibration
for external 1D data and the current BL19B2 2D workflow. It builds on pyFAI and
FabIO rather than reimplementing detector integration and image access. The
scholarly contribution is the explicit intensity-state and correction-history
contract across calibration, external-profile scaling, and traceable export--a
boundary not provided by those dependencies. The Python API, command line, and
Workbench share those numerical and I/O modules, but they are not equivalent
front ends. CLI `estimate-k` and `subtract-buffer` apply the intensity-state
gates; `norm-factor`, `parse-header`, and `parse-external1d` remain thin
utilities. The Workbench is not a substitute for the strict campaign runner.
Geometry calibration and model fitting remain with the specialist tools above.

# Software design

The software separates user interfaces from reusable scientific and I/O modules
(\autoref{fig:workflow}). The `saxsabs.core` modules implement normalization,
detector reduction, calibration, material attenuation, recorded-intensity-state
assessment, preflight validation, reference matching, and uncertainty handling. `saxsabs.io`
parses heterogeneous headers and 1D tables and writes canSAS1d 1.1 XML and
NXcanSAS 1.1 HDF5 [@cansas1d; @nxcansas]. The strict BL19B2 workflow validates
detector, monitor, transmission, thickness, reference, and output inputs before
integration, calibration, and export. CLI subcommands cover normalization,
parsing, gated $K$ estimation, and gated buffer subtraction; the SAXSAbs
Workbench adds interactive calibration, batch processing, and external-1D
conversion (\autoref{fig:gui}).

The design deliberately separates a bounded, strict BL19B2 campaign schema from
the more general calculation and I/O APIs. A permissive all-beamline workflow
would accept more files but would require silent assumptions about metadata and
correction history. The narrower strict path instead fails when those contracts
cannot be established, while the reusable modules remain available for other
interfaces. This trades immediate format breadth for auditable scientific state.

![Architecture and data flow. The Python API, command line, and Workbench share numerical and I/O modules. Before writing absolute-intensity data, the software checks physical inputs, processing history, and output state. The diagram is derived from the public package modules and interfaces; no experimental data are shown.](fig_workflow.png){#fig:workflow width="100%"}

To estimate $K$, `saxsabs` interpolates a measured standard profile onto the
reference grid and calculates
$R_i=I_{\mathrm{ref}}(q_i)/I_{\mathrm{meas}}(q_i)$. It defines the median ratio
as $\tilde{R}$ and
$\hat{\sigma}=1.4826\,\mathrm{median}(|R_i-\tilde{R}|)$, retains ratios within
$3\hat{\sigma}$, and uses their median as $K$. Isolated anomalous ratios are
excluded by this filter on user-supplied references; the built-in SRM 3600 path
additionally fails closed if any ratio exceeds the certificate-derived
relative-intensity limit before filtering. The software reports the dispersion
of retained ratios separately from combined calibration uncertainty and
propagates supported independent input uncertainties when supplied; unavailable
terms remain unspecified. The BL19B2 workflow reports a partial combined standard uncertainty
when shared covariance terms are not quantified and does not report a system
expanded uncertainty in that case.

The attenuation functionality follows two distinct data paths. Its general
diagnostic calculator obtains energy-dependent elemental coefficients from the
Elam database through `xraydb.mu_elam` [@elam2002; @xraydb]. Its fixed 30 keV
material calculation uses a versioned NIST SRD 126 snapshot [@nist_srd126].
Absolute 1D intensity is reported in cm$^{-1}$ only when the writer receives
`intensity_state=absolute_cm^-1` and an explicit cm$^{-1}$ unit; a unitless
`absolute` label is not treated as cm$^{-1}$. CSV and TSV outputs are directly
inspectable; the structured XML and HDF5 outputs follow the documented canSAS1d
1.1 and NXcanSAS 1.1 layouts. Project-local tests cover those layouts. An
offline check on 15 August 2026 validated the deterministic example against the
official canSAS1d 1.1 XSD and `punx` 0.3.5 [@punx] with bundled v2018.5
definitions; that check is not in CI, and current NeXus definitions and
third-party consumers have not been verified.

![SAXSAbs Workbench in English, showing K-calibration inputs and the plotting area. The screenshot was captured from the current source tree and contains no beamline data.](fig_gui.png){#fig:gui width="100%"}

# Software availability

Source code, tests, documentation, and examples are available in the [SASAbs
GitHub repository](https://github.com/D-sudoasd/AbsSAXS) under the BSD-3-Clause
license. The core package supports Python 3.10 and later; optional dependency
groups enable Workbench, detector-image, BL19B2, and HDF5 functionality. The
README includes installation instructions and minimal commands. Reviewers
should use the unreleased 2.0.0 tree on `main`, not GitHub Release v1.1.1.
Archived earlier releases are collected in the Zenodo concept record
[@saxsabs_archive].

# Research impact statement

The repository includes a strict BL19B2 batch workflow from detector images to
exported results. Its deterministic example in `examples/minimal_2d/` plants
synthetic dark, background, standard, and sample frames on a 9×9 array;
subtracts a NIST blank in detector space; reduces with a homemade integer-bin
radial average (not pyFAI); recovers the planted $K$ and sample curve within
script tolerances; and writes labeled absolute text/XML with unknown
uncertainty. It does not exercise the BL19B2 campaign runner or third-party
format validation. Automated tests cover numerical calculations, parsers,
exporters, the command-line interface, launchers, and Workbench validation
rules.
The repository configures continuous integration for Python 3.10--3.13 on Linux,
Windows, and macOS.

The tests and synthetic example verify implemented calculations, interfaces,
metadata handling, and output generation. They do not by themselves establish
research impact. The author uses `saxsabs` as the absolute-intensity step for
SAXS measurements of metallic materials at SPring-8 BL19B2, including the
SAXS/USAXS campaign reported in Gong et al. [@gong2026acta] and subsequent
beamtime on the same line. Detector images and reduced 1D profiles are
converted to cm$^{-1}$ with recorded $K$, thickness, transmission, and
intensity state; those absolute profiles are the intensities used in the
materials analysis. That article does not cite `saxsabs`. Beamline-private
raw frames are not in this repository; the author can provide editor-visible
processing records.

# AI usage disclosure

GitHub Copilot, Anthropic Claude, OpenAI Codex, and xAI Grok assisted with
code refactoring, internationalization, test scaffolding, documentation,
repository review, figure generation, and manuscript editing. Exact versions
of some earlier tools were not retained. The author reviewed, edited, and
validated AI-assisted output against source code, automated tests, and cited
primary sources; made the scientific, architectural, and design decisions;
and is responsible for the software, manuscript, and submission.

# Author contributions

Delun Gong: Conceptualization, Data curation, Investigation, Methodology,
Project administration, Resources, Software, Validation, Visualization,
Writing - original draft, and Writing - review and editing.

# Acknowledgements

No external funding was received for this software. The sponsor role is
therefore not applicable. The author declares no competing interests.

# References
