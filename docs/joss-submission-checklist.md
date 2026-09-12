# JOSS submission checklist

This checklist follows the current JOSS author and reviewer documentation,
accessed 27 August 2026. It is a release-readiness snapshot for the unreleased
2.0.0 source candidate on `main`; the stable archived assets remain Release
v1.1.1.

- [Submission requirements](https://joss.readthedocs.io/en/latest/submitting.html)
- [Paper format](https://joss.readthedocs.io/en/latest/paper.html)
- [Review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html)
- [AI usage policy](https://joss.readthedocs.io/en/latest/submitting.html#ai-usage-policy)

## Pre-review screening gates

- [x] **More than six months of public development.** GitHub reports that this
      repository was created on 25 February 2026. Planned submission is
      13 September 2026, which is after the conservative eligibility date of
      26 August 2026. Public releases, pull requests, and CI span that interval.
- [x] **Demonstrated research use.** The author uses saxsabs as the
      absolute-intensity step for SAXS/USAXS at SPring-8 BL19B2, including the
      campaign reported in Gong et al., Acta Materialia 316 (2026) 122455.
      That article does not cite saxsabs. Synthetic tests do not substitute for
      this author-declared research workflow.
- [x] **Good open-source practices.** The project has an OSI-approved license,
      packaging metadata, archived earlier releases, a changelog, tests, CI configuration, documentation,
      contribution guidance, support pathways, and issue/PR templates.
- [x] **Iterative development.** The public history contains releases and
      functional, safety, test, documentation, and packaging changes across the
      available public period. This does not waive the six-month gate.

## Repository and documentation

- [x] BSD-3-Clause `LICENSE` file.
- [x] Source installation and optional dependencies documented in `README.md`.
- [x] CLI, GUI, core API, and minimal example documented.
- [x] Core API reference in `docs/api.md`.
- [x] Architecture and scientific boundaries in `docs/architecture.md`.
- [x] Automated tests and a configured Linux/Windows/macOS CI matrix for Python
      3.10--3.13.
- [x] `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, bug/feature templates, and a PR
      template.
- [x] `CITATION.cff` and `codemeta.json` identify the canonical repository
      without presenting the project concept DOI as an exact 2.0.0 archive.
      README, paper, and `.zenodo.json` label the concept DOI at project level.
- [ ] Immediately before submission, record green push and Draft-PR runs for
      the exact submitted HEAD in the dated external validation record. Do not
      embed a self-referential commit hash in this tracked checklist.
- [ ] Confirm that the submitted branch and 40-character SHA identify the same
      revision as the visible public README, paper blobs, and successful CI run.
- [ ] Verify that the public repository description, homepage concept DOI,
      visible README, and submitted branch identify the same candidate.
- [ ] Run `scripts/check_public_candidate.py` against the completed confirmation
      JSON and retain its PASS output. If the paper is not on `main`, post the
      reported `branch-where-paper-is` command in the JOSS pre-review issue.

## Paper

- [x] `paper/paper.md` uses JOSS Markdown/YAML metadata.
- [x] The body is within the 750--1750 word range by the documented Pandoc
      plain-text count, excluding References and author-input markers; rerun the
      readiness gate after author-controlled content is added.
- [x] Required sections are present: Summary, Statement of need, State of the
      field, Software design, Research impact statement, AI usage disclosure,
      Acknowledgements, and References.
- [x] Related software and scientific sources have been checked against DOI or
      official records.
- [x] The paper distinguishes xraydb/Elam from the NIST SRD 126 fixed-energy
      table and does not describe either as XCOM.
- [x] The workflow figure has editable SVG/PDF sources and the GUI image is a
      window-scoped capture of the actual Workbench.
- [x] canSAS1d XML from the deterministic example validated offline on
      15 August 2026 against the official version 1.1 XSD with zero errors.
      That check is not in CI.
- [ ] NXcanSAS HDF5 passed punx 0.3.5 offline on 15 August 2026 with its
      bundled v2018.5 definitions; that check is not in CI. Current NeXus
      definitions and a third-party application consumer remain unverified
      because punx 0.3.5 cannot parse the current definition set.
- [x] The author confirms author order, affiliation, corresponding author,
      acknowledgements, funding, conflicts of interest, and contribution roles.
- [x] The author confirms the AI disclosure and human review statement in
      `paper/paper.md` (Copilot, Claude, Codex, Grok; earlier versions not
      retained).
- [x] The author supplies research-use evidence suitable for the impact
      section (author-declared BL19B2 workflow; Acta 2026 as public context,
      not a software citation).
- [ ] Measured beamline/scientific acceptance is archived with raw inputs,
      repeatability, and an independent comparison. This is a project extra,
      not a JOSS must-meet desk-reject gate. Synthetic validation and
      engineering tests do not satisfy that extra gate.
- [x] The current official Inara workflow converts the paper to TeX and
      well-formed JATS with citations and figures resolved.
- [x] The current candidate PDF was built from Inara-generated TeX with
      LuaLaTeX, and its figures, references, page bounds, fonts, and rendered
      pages were checked. Rebuild it if author-controlled content changes.

## Post-review release and archive

These items follow successful JOSS review and are required before acceptance,
not before the initial submission:

- [ ] Freeze the exact reviewed revision and create the approved version tag.
- [ ] Create the matching GitHub Release with verified wheel and source distribution.
- [ ] Archive that reviewed revision with Zenodo or another accepted archive and
      record the version DOI.
- [ ] Align the archive title, version, author list, and DOI with the final paper.
- [ ] Report the final software version and archive DOI in the JOSS review issue.

All unchecked remote actions require the repository owner's explicit approval.
