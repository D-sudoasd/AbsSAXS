# Submission readiness snapshot

Updated: 13 September 2026

Review the current unreleased 2.0.0 source candidate on `main`; the stable
archive is GitHub Release v1.1.1 and its release assets. `v2.0.0` remains
unreleased: do not create its tag, GitHub Release, or Zenodo version archive
until JOSS review completes.

## Author-controlled statements (in `paper/paper.md`)

- Sole author and corresponding author: Delun Gong, `dlgong@imr.ac.cn`,
  ORCID 0000-0001-7877-7707.
- Paper YAML date: 13 September 2026.
- Research use: the author uses saxsabs as the absolute-intensity step for
  SAXS/USAXS at SPring-8 BL19B2, including the campaign reported in Gong et al.,
  Acta Materialia 316 (2026) 122455. That article does not cite saxsabs.
  Beamline-private raw frames are not in the repository.
- AI disclosure: GitHub Copilot, Anthropic Claude, OpenAI Codex, and xAI Grok;
  earlier exact versions not retained; author reviewed outputs and remains
  responsible.
- Funding: no external funding. Competing interests: none.

## Mechanical checks that remain at the submitted HEAD

Do not embed a commit SHA in this file. Immediately before clicking submit:

1. Public history still exceeds six months (created 25 February 2026).
2. `paper/paper.md` date matches the calendar day of submission.
3. The public GitHub description, homepage concept DOI, visible README, and
   submitted branch identify the same candidate.
4. The exact submitted HEAD has a green CI run (tests plus the paper job).
5. Run, on a clean worktree with Pandoc available:

```bash
python scripts/check_submission_readiness.py \
  --as-of 2026-09-13 \
  --manual-confirmations path/to/submission-confirmations.json
python scripts/check_public_candidate.py \
  --confirmations path/to/submission-confirmations.json
```

The confirmation JSON belongs in the dated external validation record (desktop
submission pack), not in this tracked file.

## Project extra (not a JOSS desk-reject gate)

Measured beamline/scientific acceptance with archived raw inputs, repeatability,
and an independent comparison is still open. Synthetic `minimal_2d` and CI tests
do not satisfy that extra gate.

## After review

JOSS asks authors to tag the reviewed revision and archive it. Do not create
`v2.0.0` before that request.
