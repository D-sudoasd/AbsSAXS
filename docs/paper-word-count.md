# JOSS paper word-count method

The JOSS submission-length gate counts the manuscript body as rendered by
Pandoc, excluding the References section and any `[Author input required ...]`
markers. It tokenizes that plain text with
`[A-Za-z0-9][A-Za-z0-9'./+^-]*`; the permitted range is 750–1,750 words.

Current manuscript body count: **1,211 words** (Pandoc 3.11, 26 September 2026).
Regenerate after any manuscript edit and update this dated value if it changes.

Regenerate the count from the project root after any manuscript edit:

```powershell
$env:PANDOC = "C:\path\to\pandoc.exe"
py -3.13 -c "from scripts.check_submission_readiness import paper_word_count; print(paper_word_count())"
```

Pandoc must be available on `PATH` or its executable set in the `PANDOC`
environment variable. This uses the same conversion and token rule as the
submission-readiness check. The generated value is authoritative for the
current revision.
