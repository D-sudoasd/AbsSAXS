# JOSS submission checklist

Updated 26 September 2026 against the current JOSS author and reviewer
documentation.

- [Submission requirements and AI usage policy](https://joss.readthedocs.io/en/latest/submitting.html)
- [Paper format](https://joss.readthedocs.io/en/latest/paper.html)
- [Review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html)
- [Review checklist](https://joss.readthedocs.io/en/latest/review_checklist.html)

## Current candidate

- Package version: `2.0.0`, currently unreleased.
- Latest GitHub Release: `v1.1.1` from 21 April 2026; earlier release:
  `v1.0.0` from 26 February 2026.
- The public repository was created on 25 February 2026. Its history contains
  commits from February through September, seven merged pull requests, tagged
  releases, CI, tests, documentation, contribution instructions, and an issue
  tracker. This satisfies the more-than-six-month public-history period as of
  26 September; JOSS will still assess the full commit distribution and
  iteration.
- The exact candidate commit's successful CI run and the inspected JOSS PDF
  are recorded in the dated desktop submission package. That record also
  identifies the source and distribution hashes; rerun these checks if the
  candidate changes.
- No `v2.0.0` release has been published. This project's plan is to stage the
  candidate assets in a GitHub Draft Release targeted at the submitted commit,
  then publish the final reviewed revision after review. JOSS asks for the
  reviewed revision to be tagged and archived after review; it does not
  prohibit draft or pre-release work before then. The current tag-triggered
  workflow publishes a GitHub Release, so pushing a tag would publish it.

## JOSS screening and repository practice

- [x] Public source repository, browsable without registration, with an issue
      tracker open to public reports and code proposals.
- [x] OSI-approved BSD-3-Clause license in `LICENSE`.
- [x] Public history spans more than six months and shows changes across that
      period, not only the recent submission-preparation commits.
- [x] Public tags/releases, pull requests, CI, tests, user documentation,
      `CONTRIBUTING.md`, and support expectations are present.
- [x] The author has declared real use of `saxsabs` in the SPring-8 BL19B2
      SAXS/USAXS research workflow. Gong et al., *Acta Materialia* 316 (2026)
      122455 is contextual research evidence and does not cite the software;
      do not describe it as a software citation.
- [ ] The final paper gives concise, specific research-use evidence and does
      not claim external adoption or a software citation without evidence.
- [ ] The final submitted commit has a green full CI run and its test,
      distribution, and paper-PDF artifacts have been checked.
- [ ] The public README, repository metadata, paper, submitted branch, exact
      commit, and successful Actions run describe the same candidate.

JOSS's current criteria require research use at minimum by the developers;
use by other groups is desirable but not a prerequisite. For a single-author
project, several public-development signals can establish open practice; a
multi-author contribution history is not required by itself. The editor
decides scope and significance based on the whole record.

## Paper format

- [ ] Markdown paper with valid JOSS YAML metadata and the actual submission
      date in `D Month YYYY` format.
- [ ] Body is 750–1,750 words under the Pandoc count used by
      `scripts/check_submission_readiness.py`.
- [ ] Required sections: `Summary`, `Statement of need`, `State of the field`,
      `Software design`, `Research impact statement`, `AI usage disclosure`,
      `Acknowledgements`, and `References`.
- [ ] The paper explains the software for non-specialists, its target research
      users, related software, design trade-offs, and research use. Keep API
      documentation in the repository documentation.
- [ ] References include related software and full venue names, and the cited
      archive DOI points to the exact reviewed version once it exists.
- [ ] Acknowledgements describe funding and sponsor involvement, or state
      accurately that there was no external funding.
- [ ] AI disclosure covers software, documentation, figures, and manuscript
      assistance used through the final candidate; lists tools/models and
      versions where known, locations, and kinds of assistance; and describes
      the verification performed.
- [ ] Before submission, the human author reviews, edits, and validates every
      AI-assisted output in the final candidate and confirms the core design
      decisions. The 13 September 2026 confirmation applies only to the earlier
      candidate and does not attest to outputs added after that date.
- [ ] The PDF generated from the final submitted commit by the JOSS Inara
      workflow is inspected. Older local or desktop PDFs do not validate a new
      paper revision.

## Final local and remote gates

Run from a clean checkout of the exact submitted commit after merging the
final candidate and recording the successful Actions URL:

```powershell
$env:PANDOC = ".audit-work/tools/pandoc-3.11/pandoc-3.11/pandoc.exe"
py -3.12 scripts/check_submission_readiness.py `
  --as-of YYYY-MM-DD `
  --manual-confirmations "D:\path\to\submission-confirmations.json"
py -3.12 scripts/check_public_candidate.py `
  --confirmations "D:\path\to\submission-confirmations.json"
```

Use the real submission date and the confirmation record for that exact commit.
Keep the dated JSON and command output in the desktop submission package, not
in the repository. Run the two commands again if the paper or candidate commit
changes.

## After successful review

- [ ] Freeze the revision approved by the JOSS editor.
- [ ] Create the matching version tag; let the release workflow validate the
      tag and publish its verified wheel and source distribution.
- [ ] Archive that exact revision with Zenodo or another accepted service.
- [ ] Check archive title, version, author list, license, and version DOI.
- [ ] Report the version and archive DOI in the public JOSS review issue.
