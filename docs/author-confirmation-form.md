# Author confirmation form

Completed from the corresponding author's statements on 12 September 2026.
Use this record with `paper/paper.md`; do not infer undeclared facts.

## Authorship and correspondence

- Final author list in order: Delun Gong
- Corresponding author: Delun Gong
- Corresponding email: dlgong@imr.ac.cn
- Affiliation(s), including city and country: Institute of Metal Research, Chinese Academy of Sciences, Shenyang 110016, China
- ORCID for each author: 0000-0001-7877-7707
- Confirmation that every listed author agrees to authorship and accountability: yes (sole author)

## Research use

- Research question or experiment: absolute-intensity SAXS of metallic materials, including spinodally modulated Ti-24Nb-4Zr-8Sn
- Software version or commit used: current unreleased 2.0.0 tree on `main` for ongoing work
- Input data type and instrument/workflow: detector images and 1D profiles from SPring-8 BL19B2 SAXS/USAXS
- Commands or interface used: saxsabs calibration and BL19B2 workflow
- Outputs used in the research: absolute-scale profiles (cm⁻¹) with recorded K, thickness, transmission, and intensity state
- How `saxsabs` affected the analysis: it is the absolute-intensity calibration step before materials interpretation
- Public paper, preprint, data, workflow, or editor-visible evidence: Gong et al., Acta Materialia 316 (2026) 122455, doi:10.1016/j.actamat.2026.122455; subsequent BL19B2 beamtime (raw frames remain beamline-private)
- Independent/external users or integrations, if any: none declared

## AI usage disclosure

JOSS requires this section. The author asked not to expand a tool/version table.
Earlier exact versions were not retained. The paper states the tools and the
author's review responsibility.

| Product | Model/version/date | Code/docs/paper locations | Nature and scope |
| --- | --- | --- | --- |
| GitHub Copilot | version not retained | code, tests, docs | refactoring, scaffolding |
| Anthropic Claude | version not retained | code, docs, paper | refactoring, documentation, editing |
| OpenAI Codex | version not retained | code, docs, paper | refactoring, tests, documentation, editing |
| Other | none declared | | |

Confirm verbatim if true:

> All human authors reviewed, edited, and validated every AI-assisted output
> included in the submitted software, documentation, figures, and manuscript.
> The human authors made the core scientific, architectural, and design
> decisions and accept full responsibility for the submission.

- Confirmation: yes

## Funding, acknowledgements, sponsor role, and competing interests

- Funding organization(s), grant number(s), or “No external funding”: No external funding
- Sponsor role in study design, software development, analysis, interpretation,
  manuscript preparation, and submission decision: not applicable
- People/facilities to acknowledge: none declared beyond the research-use beamline
- Competing interests, or explicit “The authors declare no competing interests”:
  The author declares no competing interests

## CRediT contributions

| Author | Confirmed CRediT roles |
| --- | --- |
| Delun Gong | Conceptualization, Data curation, Investigation, Methodology, Project administration, Resources, Software, Validation, Visualization, Writing - original draft, Writing - review and editing |

## Final checks

- Actual submission date (`D Month YYYY`): 12 September 2026 (paper YAML; change if submitted later)
- `paper.md` date updated to the actual submission date: yes, for 12 September 2026
- Strict readiness command returns PASS: not yet (requires confirmation JSON, green CI on that HEAD, and Pandoc)
- Confirmation JSON copied from `docs/submission-confirmations.example.json`,
  completed from evidence, and passed with `--manual-confirmations`: not yet
- Public CI URL for the submitted revision: not yet
- Commit SHA submitted to JOSS: not yet
- Public repository description, homepage concept DOI, default branch or
  submitted branch, and visible README all match that commit: not yet
- Confirmation date (`YYYY-MM-DD`, matching the paper submission date): 2026-09-12
- Research-evidence reference retained for editorial verification: doi:10.1016/j.actamat.2026.122455
- Submitted branch recorded in the confirmation JSON: not yet
- Confirmed commit is the current clean HEAD of that submitted branch: not yet
- Public-candidate command returns PASS and its editorialbot branch instruction
  (if any) has been retained for the pre-review issue: not yet

The software tag, GitHub Release, and exact-version archive DOI are created
after successful JOSS review and recorded in the review issue before acceptance.
