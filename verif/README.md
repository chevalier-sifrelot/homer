# verif

A template conformance checker for the `waiki` knowledge base.

`verify.py` reads a template in `templates/` and derives the rules a conforming
entry must satisfy, then checks entries against them. It is **template-driven**:
if the templates change, the checker follows — no code edit needed.

## What it checks

### Template conformance (always)

1. **Frontmatter** — every key declared in the template's frontmatter is present,
   non-empty, and not left as the placeholder text.
2. **Infobox** — the metadata table under the title (rows like `| **Kind** | ... |`)
   is present, and each displayed value matches the matching frontmatter value.
3. **Sections** — every `## Heading` in the template exists in the entry.
4. **Wikilinks** — any frontmatter value written as `[[name]]` points to an
   existing character file `waiki/character/name.md`.

### Quotation conformance (`--content`)

Every quotation in an entry is checked against the source texts in
`sources/raw/`, and its citation must name the book the words come from.

The rule is stated in terms of **words**, which is what makes it predictable:

- **Formatting is ignored**, because it reflects how a quotation is written down
  rather than what the text says: whitespace and line wrapping (Butler's prose
  wraps mid-sentence, so a quotation routinely spans several lines), the shape of
  the quotation marks (a quotation delimited by `"` cannot nest a literal `"`, so
  inner quotes are written `'`), letter case (a quotation folded into a sentence
  starts lowercase), and punctuation.
- **Words are not negotiable.** A word added, removed or altered is an error —
  including a word silently dropped to skip a narrator's interjection. Where the
  source reads `"Jove," he cried, "grant that…`, an entry may not quote
  `"Jove, grant that…"` as one run.
- **An omission must be explicit.** `...` marks a cut, and the fragments on
  either side must occur *in that order* within the cited book.

Errors report where a quotation stops matching, so the fix is mechanical:

```
waiki/character/hermes.md
  diverges from the source after 4 word(s) (in the Odyssey, Book V):
  source has "...said mercury or jove", entry has "...or jove will be"
```

A quotation whose words are correct but which carries no `(Iliad, Book N)`
citation is reported as a **warning**, since short quoted phrases are sometimes
turns of phrase rather than citations. Warnings do not fail the run unless
`--strict` is given.

## Usage

```bash
# Template conformance for every entry in waiki/ (character + location)
python3 verif/verify.py

# Template conformance *and* quotation conformance
python3 verif/verify.py --content

# Verify specific files (template chosen from the parent folder name)
python3 verif/verify.py --content waiki/location/troy.md

# Force a template explicitly
python3 verif/verify.py --template templates/LOCATION.md waiki/location/troy.md

# Emit GitHub Actions annotations instead of plain text
python3 verif/verify.py --content --format=github

# Make warnings fail too
python3 verif/verify.py --content --strict
```

Exit code is `0` if all checked files pass, `1` otherwise — suitable for a
pre-commit hook or CI step. `.github/workflows/verify.yml` runs
`--content --format=github` on every push and every pull request, so a failing
quotation is annotated on the diff at the exact line.

## Adding a new entry type

Add the folder → template mapping in `FOLDER_TEMPLATE` at the top of
`verify.py` (e.g. `"object": "templates/OBJECT.md"`), and the checker will apply
that template to files in `waiki/object/`.

No third-party dependencies — standard-library Python 3 only.
