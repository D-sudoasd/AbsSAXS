# Submission readiness snapshot

Updated: 27 August 2026 (Asia/Shanghai)

Review the current unreleased 2.0.0 source candidate on `main`; the stable
archive is GitHub Release v1.1.1 and its release assets. `v2.0.0` remains
unreleased: do not create its tag, GitHub Release, or Zenodo version archive
during this review.

## Locally verified

- Full source suite: PASS under Python 3.11 and 3.12, with
  `py -3.11 -B -m pytest -q -p no:cacheprovider --tb=short -W error` and the
  equivalent Python 3.12 command each reporting `1155 passed`.
- Full repository Ruff check: PASS.
- Current `git diff --check`: PASS.
- Distribution smoke from a clean temporary clone outside the checkout: sdist
  and wheel builds, fresh-venv installation of `wheel[gui,hdf5]`, CLI/import/
  `pip check`, and the `minimal_2d` synthetic smoke all PASS. The temporary
  clone path is intentionally omitted because it is not durable evidence.
- Python 3.10 and 3.13 remain pending the remote CI matrix; the local full-suite
  evidence above covers only Python 3.11 and 3.12.
- README: 5 local images and all local links resolve; SVG/image audit passes.
- Minimal 2D example: 9×9 homemade radial average (not pyFAI) recovers planted
  K and sample maximum relative errors of `0.001933697...`; CSV, TSV, XML, and
  HDF5 outputs are written with unknown uncertainty. This synthetic smoke is
  an engineering/reproducibility check, not BL19B2 measured scientific
  acceptance.
- Paper: 1228-word body by the documented Pandoc method; 16 references; current
  Inara TeX and well-formed JATS resolve both figures.
- Review PDF: the official CI paper job produces a five-page draft whose pages,
  bounds, figures, citations, and embedded fonts have been visually checked.
  Exact run URL, byte size, and SHA-256 belong in the dated external validation
  record because CI evidence must identify the submitted commit. The 1280 x 900
  GUI image is a real, reproducible full-window Workbench capture.
- Public CI gate: immediately before submission, the exact submitted HEAD must
  have green push and Draft-PR runs for the complete matrix. Immutable commit
  IDs and run URLs belong in the dated external validation record rather than
  this tracked file, because editing the evidence here creates a new HEAD.
- External format checks (offline 15 August 2026, not in CI): the deterministic
  example's canSAS1d XML validated against the official 1.1 XSD with zero
  errors. Its NXcanSAS HDF5 output passed punx 0.3.5 with bundled v2018.5
  definitions (97 OK, 0 WARN, 0 ERROR); current NeXus definitions and
  third-party consumers remain unverified.

## Must be resolved before submission

1. Recheck the public-history gate on or after 26 August 2026. JOSS requires
   more than six months of public, iterative development; the repository was
   created on 25 February 2026.
2. Add a verifiable research-use case. Synthetic validation and tests do not
   establish demonstrated research impact.
3. Confirm the complete author list/order, corresponding author, current email,
   affiliations, ORCIDs, and contribution roles.
4. Complete the AI disclosure with recoverable product/model/version details,
   usage scope, and the author's final human-review assertion.
5. Supply truthful funding, sponsor-role, acknowledgement, and competing-
   interest statements.
6. Before submission, verify that the public GitHub description, homepage
   concept DOI, visible README, submitted branch, and green CI all identify the
   exact candidate revision.
7. Complete measured beamline/scientific acceptance with archived raw inputs,
   repeatability, and an independent comparison; synthetic validation and
   engineering tests do not satisfy this gate.
Run the strict decision gate with Pandoc available:

```bash
python scripts/check_submission_readiness.py \
  --as-of YYYY-MM-DD \
  --manual-confirmations path/to/submission-confirmations.json
```

The gate must run on the exact branch and commit submitted to JOSS. Record the
submitted branch and 40-character SHA, and require that the local/public
README, paper blobs, and successful CI run all resolve to that same revision.
Evidence from an earlier commit does not cover a later commit.

After that local PASS, run:

```bash
python scripts/check_public_candidate.py \
  --confirmations path/to/submission-confirmations.json
```

This second fail-closed gate uses the public GitHub API to verify the repository,
concept-DOI homepage, license, submitted branch and SHA, visible README and
paper blobs, and successful CI run for that exact SHA. It also reports the
editorialbot branch command when the paper is not on `main`.

The current strict result is intentionally **FAIL** because the paper still has
four author-input placeholders, no confirmed corresponding author, and no paper
email. No research-use evidence or measured scientific acceptance is recorded
as complete. The mechanical preflight passes when
`--allow-author-placeholders --as-of 2026-08-26` is used; this override is not a
submission authorization.

## Review-completion actions

JOSS asks authors to make a tagged release and archive the reviewed revision
after successful review. Do not create `v2.0.0`, a GitHub Release, or a Zenodo
version archive until the candidate revision and remote workflow have been
confirmed.

The paper source is dated 26 August 2026, the earliest conservative submission
date. If submission occurs later, update the YAML date to the actual submission
date; the strict readiness gate will reject a mismatch.

The local review PDF still shows Inara pre-submission placeholders such as
`DOI: N/A`, 1970 dates, and volume/page fields. They are build metadata supplied
by the publication workflow, not text in `paper/paper.md`.
