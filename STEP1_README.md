# Step 1 — Normalize the Current Professional Identity

This package changes the present-day website identity from:

- `Prof. Dr. Ahmad Saylam`

to:

- `Dr. Ahmad Saylam`

It also changes the Person JSON-LD property:

- `"honorificPrefix": "Prof. Dr."`

to:

- `"honorificPrefix": "Dr."`

## Strict scope

Only these five files are eligible for modification:

- `index.html`
- `selected-work.html`
- `research-tools.html`
- `publications.html`
- `about-cv.html`

The script does **not** modify the `papers/` or `publications/` article pages and therefore does not alter historical publication records.

## Use

1. Copy `step1_normalize_identity.py` into the root of the downloaded or cloned website repository.
2. Open a terminal in that repository folder.
3. Preview the change:

```bash
python step1_normalize_identity.py
```

4. Apply the change after the preview passes:

```bash
python step1_normalize_identity.py --apply
```

The script then:

- creates timestamped backups of the five original files;
- applies only the two approved exact replacements;
- checks that no old current-identity marker remains;
- checks that no file outside the five-page scope changed;
- writes `IDENTITY_PATCH_REPORT.md`.

## Git verification before publishing

```bash
git diff -- index.html selected-work.html research-tools.html publications.html about-cv.html
git status
```

The diff should contain only identity normalization. Do not commit the timestamped backup directory.

Recommended commit message:

```text
Normalize current professional identity to Dr. Ahmad Saylam
```
