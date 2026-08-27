# verif

A template conformance checker for the `waiki` knowledge base.

`verify.py` reads a template in `templates/` and derives the rules a conforming
entry must satisfy, then checks entries against them. It is **template-driven**:
if the templates change, the checker follows — no code edit needed.

## What it checks

1. **Frontmatter** — every key declared in the template's frontmatter is present,
   non-empty, and not left as the placeholder text.
2. **Infobox** — the metadata table under the title (rows like `| **Kind** | ... |`)
   is present, and each displayed value matches the matching frontmatter value.
3. **Sections** — every `## Heading` in the template exists in the entry.
4. **Wikilinks** — any frontmatter value written as `[[name]]` points to an
   existing character file `waiki/character/name.md`.

## Usage

```bash
# Verify every entry in waiki/ (character + location)
python3 verif/verify.py

# Verify specific files (template chosen from the parent folder name)
python3 verif/verify.py waiki/location/troy.md

# Force a template explicitly
python3 verif/verify.py --template templates/LOCATION.md waiki/location/troy.md
```

Exit code is `0` if all checked files conform, `1` otherwise — suitable for a
pre-commit hook or CI step.

## Adding a new entry type

Add the folder → template mapping in `FOLDER_TEMPLATE` at the top of
`verify.py` (e.g. `"object": "templates/OBJECT.md"`), and the checker will apply
that template to files in `waiki/object/`.

No third-party dependencies — standard-library Python 3 only.
