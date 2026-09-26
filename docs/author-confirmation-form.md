# Author confirmation form

The corresponding author's declarations for the 13 September 2026 candidate
are carried forward with their original date; they do not need to be confirmed
again. The current candidate is prepared for submission on 26 September 2026,
and the paper date is aligned to that planned date. If submission moves to a
different calendar day, update the paper date and readiness record. Do not
infer undeclared facts.

## Authorship and correspondence

- Final author list in order: Delun Gong
- Corresponding author: Delun Gong
- Corresponding email: dlgong@imr.ac.cn
- Affiliation(s), including city and country: Institute of Metal Research, Chinese Academy of Sciences, Shenyang 110016, China
- ORCID for each author: 0000-0001-7877-7707
- Confirmation that every listed author agrees to authorship and accountability: yes (sole author)

## Research use

- Research question or experiment: absolute-intensity SAXS of metallic materials, including spinodally modulated Ti-24Nb-4Zr-8Sn
- Software version or commit used: current unreleased 2.0.0 candidate for ongoing work
- Input data type and instrument/workflow: detector images and 1D profiles from SPring-8 BL19B2 SAXS/USAXS
- Commands or interface used: saxsabs calibration and BL19B2 workflow
- Outputs used in the research: absolute-scale profiles (cm⁻¹) with recorded K, thickness, transmission, and intensity state
- How `saxsabs` affected the analysis: it is the absolute-intensity calibration step before materials interpretation
- Public paper, preprint, data, workflow, or editor-visible evidence: Gong et al., Acta Materialia 316 (2026) 122455, doi:10.1016/j.actamat.2026.122455, as the public SAXS/USAXS research context at BL19B2. That article does not cite saxsabs. Subsequent BL19B2 beamtime (raw frames remain beamline-private); editor-visible processing records on request.
- Independent/external users or integrations, if any: none declared

## AI usage disclosure

The following inventory records the corresponding author's declaration for
the 13 September 2026 candidate. The earlier exact versions were not retained.
The recorded author review covered the outputs in that candidate only.

| Product | Model/version/date | Code/docs/paper locations | Nature and scope |
| --- | --- | --- | --- |
| GitHub Copilot | version not retained | code, tests, docs | refactoring, scaffolding |
| Anthropic Claude | version not retained | code, docs, paper | refactoring, documentation, editing |
| OpenAI Codex | version not retained | code, docs, paper | refactoring, tests, documentation, editing |
| xAI Grok | version not retained | docs, paper | homepage and manuscript editing |
| Other, through 13 September | none declared | | |

The earlier author record includes this confirmation for the 13 September 2026
candidate:

> All human authors reviewed, edited, and validated every AI-assisted output
> included in the submitted software, documentation, figures, and manuscript.
> The human authors made the core scientific, architectural, and design
> decisions and accept full responsibility for the submission.

- Confirmation recorded for the 13 September 2026 candidate: yes

### AI-assisted work added during 26 September preparation

This round used OpenAI Codex with the GPT-6 model for code, tests, project
documentation, and manuscript editing. It included source changes and focused
test coverage, repository and JOSS documentation, release and package
configuration, and edits to the JOSS paper and bibliography. Python scripts
generated the scientific workflow figures, and a native capture of the
Workbench supplied the GUI figure. OpenAI's built-in image-generation tool
created the conceptual README cover illustration; the interface did not expose
the model version. That illustration is decorative and is not a scientific
result or a data-derived figure.

Technical verification performed for this candidate is recorded in the dated
desktop submission report, including the source, test, image-layout, package,
installation, and CI checks that have completed. The human author still needs
to inspect the finished package, review, edit, and validate all AI-assisted
outputs, and confirm the core design decisions. No new author confirmation of
that review is recorded here; automated and agent-performed checks do not
substitute for it.

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

## Current candidate and technical record

- Planned submission date: 26 September 2026; the paper date is set to match.
- The research-use reference retained from the earlier author declaration is
  doi:10.1016/j.actamat.2026.122455. The article is research context and does
  not cite `saxsabs`.
- The dated desktop validation record holds the exact submitted branch and
  commit, current CI run URLs, repository-identity check, package/PDF results,
  and outputs from both readiness commands. Keep those commit-specific facts
  in that record rather than in this reusable form.
- One author-only statement remains for this revision: after inspecting the
  finished submission package, the human author must affirm that all new
  AI-assisted outputs since 13 September were reviewed, edited, and validated,
  and that the core design decisions are human decisions. The earlier
  13 September confirmation does not cover those new outputs.

The software tag, GitHub Release, and exact-version archive DOI are created
after successful JOSS review and recorded in the review issue before acceptance.
