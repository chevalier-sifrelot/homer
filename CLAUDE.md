# CLAUDE.md

Guidance for Claude Code when working in this repository. See `README.md` for the
human-facing project description and `TODO.md` for open design questions.

## What this project is

Homer is a Markdown knowledge base (the `waiki`) on the mythology of Homer's
*Iliad* and *Odyssey*, built **strictly from the source texts**. Each entry is a
single Markdown file that follows a template.

## Golden rule

Every factual claim in a fiche must come **only** from the source texts in
`sources/raw/` — never from outside knowledge. Quotations must be copied
**verbatim** and attributed to the correct book (e.g. `(Iliad, Book VI)`). If you
cannot support a claim with a quote you actually found in the text, do not make it.

## Repository layout

- `sources/raw/` — `iliad.txt`, `odyssey.txt` (Samuel Butler prose translation). 24 books each, marked by lines `BOOK I` … `BOOK XXIV`.
- `templates/` — `CHARACTER.md`, `LOCATION.md`: the structure every entry must follow.
- `waiki/character/` — one file per character.
- `waiki/location/` — one file per location.
- `verif/` — `verify.py`, the template-conformance checker (+ its own README).

## Source-text conventions (important)

- Roman god names are used: **Jove** = Zeus, **Minerva** = Athena, **Neptune** = Poseidon, **Pluto/Hades** = Hades, **Mars** = Ares, **Venus** = Aphrodite, **Mercury** = Hermes, **Juno** = Hera, **Diana** = Artemis, **Vulcan** = Hephaestus.
- **Ulysses** = Odysseus.
- Troy is often called **Ilius**; Sparta is **Lacedaemon**; the Phaeacians' land is **Scheria**.
- Butler's prose wraps across lines, so one quotation may span several lines. Workflow: `grep` a short distinctive fragment → read the surrounding lines to quote accurately → confirm the book with `grep -n "^BOOK"`.

## Entry format

Each entry has YAML frontmatter, then an **infobox** table (mirroring the
frontmatter) under the H1 title, then the prose sections.

Frontmatter fields:
- Character: `Name`, `Kind` (Human|God|Creature), `Origin`, `Gender`, `AfiliatedTo` (Achaeans|Trojans)
- Location: `Name`, `Kind` (City|Island|Region|Realm|Landmark), `Region`, `Ruler`, `AfiliatedTo` (Achaeans|Trojans|Neither)

Sections:
- Character: `## Appearances`, `## Personality` (3 traits + verbatim quotes), `## Entourage` (3 characters)
- Location: `## Appearances`, `## Significance` (3 features/events + verbatim quotes), `## Inhabitants` (3 characters)

Conventions:
- **Filenames**: lowercase, hyphenated (`ajax-the-great.md`, `mount-olympus.md`).
- **Infobox values must equal the frontmatter values** — the verifier enforces this. When editing metadata, change both.
- **Cross-references are Markdown links, not wikilinks** (`[[...]]` did not render as clickable links in the target viewer):
  - Location `Ruler` → `[name](../character/name.md)`
  - Character `Origin` → `[Name](../location/name.md)` when the place has a fiche
- `AfiliatedTo` is deliberately misspelled (single "f") throughout; keep it as-is for consistency with all existing files rather than "fixing" it piecemeal.

## Adding an entry

1. Copy the relevant template from `templates/`.
2. Fill the frontmatter and mirror the values in the infobox.
3. Write each section using only source material; quote verbatim with book citations.
4. Add cross-reference links wherever a target fiche already exists.
5. Run the verifier and fix every problem before finishing.

## Verifying

```bash
python3 verif/verify.py            # check all entries
python3 verif/verify.py <file>...  # check specific files
```

Exit code `0` means conform, `1` means problems. The checker is **template-driven**:
it reads the template to derive its rules, so change the templates rather than
hard-coding rules. To support a new entry type, add a `folder → template` mapping
in `FOLDER_TEMPLATE` at the top of `verify.py`. Standard-library Python 3 only.
