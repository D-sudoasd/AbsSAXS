# Author confirmation form

The corresponding author's declarations for the 13 September 2026 candidate
are carried forward with their original date. On 26 September, the author
clarified that AI assistance before this preparation round was limited to
coding. The current candidate is prepared for submission on 27 September 2026,
and the paper date is aligned to that date. If submission moves to a different
calendar day, update the paper date and readiness record. Do not infer
undeclared facts.

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
- Public paper, preprint, data, workflow, or editor-visible evidence: Gong et al., Acta Materialia 316 (2026) 122455, doi:10.1016/j.actamat.2026.122455. On 27 September 2026, the author explicitly confirmed that saxsabs processed data for this published study and that processing records are available for editorial verification. That article does not cite saxsabs. The author also uses the software in subsequent BL19B2 work; raw frames remain beamline-private.
- The exact historical software revision and input/output identities for the published study are held in the author's processing records. The current 2.0.0 submission candidate must not be substituted for that historical revision without checking those records.
- Independent/external users or integrations, if any: none declared

## AI usage disclosure

The following inventory records the corresponding author's declaration for
the 13 September 2026 candidate, as clarified on 26 September. The earlier
exact versions were not retained. These tools assisted with coding only; they
were not used to write the earlier candidate's paper or documentation, or to
create its figures.

| Product | Model/version/date | Location | Nature and scope |
| --- | --- | --- | --- |
| GitHub Copilot | version not retained | code | coding assistance |
| Anthropic Claude | version not retained | code | coding assistance |
| OpenAI Codex | version not retained | code | coding assistance |
| xAI Grok | version not retained | code | coding assistance |
| Other, through 13 September | none declared | | |

The author confirms that this historical disclosure is limited to coding
assistance. The human-review declaration for the 13 September 2026 candidate
covered the AI-assisted code in that candidate:

> The sole author reviewed, edited, and validated the AI-assisted code. The
> author made the core scientific and software-design decisions and accepts
> full responsibility for the software.

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
installation, and CI checks that have completed. On 26 September 2026, the
corresponding author confirmed that they reviewed, edited, and validated all
AI-assisted outputs in this candidate, made the core scientific and software
design decisions, and accept responsibility for the submitted materials.
Automated checks support that review but do not replace the author's
responsibility.

### Submission update on 27 September 2026

The author confirmed actual software use in the published study and the
availability of processing records, then requested completion of the submission
materials for that evening. Codex assisted with submission dates, consistent
documentation, validation records, and package assembly. The scientific text,
figures, and software implementation were not changed by this update. The
13 September and 26 September declarations retain their original dates; the
dated candidate record identifies the new verification date and commit.

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

- Planned submission date: 27 September 2026; the paper date is set to match.
- Research use for doi:10.1016/j.actamat.2026.122455 and the availability of
  processing records were explicitly confirmed on 27 September 2026. The
  article does not cite `saxsabs`.
- The dated desktop validation record holds the exact submitted branch and
  commit, current CI run URLs, repository-identity check, package/PDF results,
  and outputs from both readiness commands. Keep those commit-specific facts
  in that record rather than in this reusable form.
- The corresponding author confirmed on 26 September 2026 that all new
  AI-assisted outputs since 13 September were reviewed, edited, and validated,
  and that the core scientific and software-design decisions are human
  decisions. The author accepts responsibility for this candidate.

The software tag, GitHub Release, and exact-version archive DOI are created
after successful JOSS review and recorded in the review issue before acceptance.
