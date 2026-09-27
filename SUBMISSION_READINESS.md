# JOSS submission readiness

Updated: 27 September 2026

## Candidate and release state

The current source candidate is version `2.0.0`. There is no published
`v2.0.0` release. GitHub's latest published release is `v1.1.1` (21 April
2026), preceded by `v1.0.0`. The repository was created on 25 February 2026.
Its public release records, development history, and author confirmation support
more than six months of public development on the date of this snapshot.

The exact candidate commit, successful CI run, inspected JOSS PDF, and package
artifacts are recorded in the dated desktop submission package. Its validation
record identifies the tested commit and artifact hashes. Re-run these checks
if the source or paper changes. The package CI job builds an sdist and wheel,
checks them with Twine, installs the wheel in a clean environment, and records
both distributions as an Actions artifact.

This project's plan is to stage candidate `2.0.0` assets in a GitHub Draft
Release targeted at the submitted commit. JOSS asks for the reviewed revision
to be tagged and archived after review; it does not prohibit draft or
pre-release work before then. The current tag-triggered workflow publishes a
GitHub Release, so pushing a tag would publish it. Keep the candidate draft
unpublished and without a tag; after the editor requests final release details,
update it to the exact reviewed revision, publish its matching version tag and
GitHub Release, archive that revision with Zenodo (or another accepted
archive), and report the version and archive DOI in the review issue.

## Author declarations carried forward

The following author-controlled statements were supplied for the 13 September
2026 candidate and are carried forward from the earlier submission record:

- Sole author and corresponding author: Delun Gong, `dlgong@imr.ac.cn`, ORCID
  `0000-0001-7877-7707`; affiliation: Institute of Metal Research, Chinese
  Academy of Sciences, Shenyang 110016, China.
- Research use: the author uses `saxsabs` for absolute-intensity SAXS/USAXS at
  SPring-8 BL19B2. On 27 September 2026, the author additionally confirmed actual
  software use in Gong et al., *Acta Materialia* 316 (2026) 122455 and the
  availability of processing records for editorial verification. The article
  does not cite `saxsabs`; this is author-confirmed use, not a software citation
  or independent external adoption. Raw beamline frames remain private.
- No external funding; no competing interests declared.
- Earlier AI tools declared by the author: GitHub Copilot, Anthropic Claude,
  OpenAI Codex, and xAI Grok. Exact earlier model versions were not retained.
  On 26 September, the author clarified that these tools assisted with coding
  only in the earlier work; they did not contribute to its paper,
  documentation, or figures.

The 13 September human-review declaration applied to AI-assisted code in that
candidate. It does not describe the broader AI assistance used during the
26 September preparation, which is disclosed separately in the current paper.
On 26 September, the corresponding author confirmed that they reviewed,
edited, and validated the AI-assisted outputs prepared on that date, made
the core scientific and software-design decisions, and accept responsibility
for the submitted materials. The dated desktop validation record contains the
commit-specific technical evidence.

The 27 September update aligns the submission date and documentation, records
the author's research-use clarification, and refreshes technical verification.
It leaves the scientific text, figures, and software implementation unchanged.
Original author-declaration dates are retained separately from the current
candidate verification date.

## JOSS paper requirements

The current JOSS format is Markdown with YAML metadata and a 750–1,750-word
body. It requires the sections `Summary`, `Statement of need`, `State of the
field`, `Software design`, `Research impact statement`, `AI usage disclosure`,
`Acknowledgements`, and `References`. The paper must identify the software
authors and affiliations, cite related software, describe applicable research
use and financial support, and keep API documentation in the repository docs
rather than the paper.

The AI disclosure must cover AI use in software development, documentation,
figures, and paper authoring. When AI tools were used, JOSS asks authors to
describe how they were used and how the generated material's quality and
correctness were checked. Report only verification that was actually
completed. The current JOSS policy also requires human authors to confirm
that they reviewed, edited, and validated all AI-assisted outputs and made the
core design decisions. The author recorded this confirmation for the
26 September candidate; see the author confirmation form and dated
desktop record.

JOSS's current screening also asks for more than six months of public
development for recently public projects, with activity over that period and
evidence such as releases, tags, issues, or pull requests. Research impact must
be specific and evidenced; the author-declared BL19B2 workflow is the current
research-use statement. The paper must not turn a contextual paper into a
software citation when it does not cite the package.

## Exact-candidate checks before submission

After the final paper and repository changes are merged to the submitted
branch:

1. Confirm that the paper date is the actual submission date and that the
   paper contains no author-input placeholders.
2. Confirm green test, package, and JOSS PDF jobs for the exact submitted
   commit. Inspect the PDF generated by the JOSS Inara workflow; an older PDF
   from a previous package is not evidence for the current paper.
3. Confirm the submitted branch and 40-character SHA match the public README,
   paper, and Actions run. Keep the confirmation JSON and command output in the
   dated desktop submission package rather than committing them.
4. Run both repository gates from a clean checkout with Pandoc available:

```powershell
$env:PANDOC = ".audit-work/tools/pandoc-3.11/pandoc-3.11/pandoc.exe"
py -3.12 scripts/check_submission_readiness.py `
  --as-of YYYY-MM-DD `
  --manual-confirmations "D:\path\to\submission-confirmations.json"
py -3.12 scripts/check_public_candidate.py `
  --confirmations "D:\path\to\submission-confirmations.json"
```

Replace `YYYY-MM-DD` with the real submission date and use the confirmation
record for that same date and exact commit. Its `confirmed_on` field identifies
the current candidate verification date; separate declaration dates preserve
when the author originally confirmed authorship, AI review, and other facts.
The strict readiness command checks
the paper, citation keys, repository metadata, README targets, versions, clean
worktree, word count, and date. The public-candidate command checks the remote
repository identity and CI evidence. The 13 September confirmation record must
not be reused as though it verifies a new commit.

## Project-level validation outside the JOSS screening gates

Measured beamline acceptance with archived raw frames, repeatability, and an
independent scientific comparison remains a separate project validation item.
Synthetic examples and CI establish software behavior only; they do not supply
that measurement evidence. This item is not a prerequisite for the initial
JOSS submission when the paper accurately describes the author's actual
research use and the software's measured claims.
