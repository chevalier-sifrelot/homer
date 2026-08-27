# Homer

A Markdown knowledge base on Ancient Greek mythology, built from a close study of Homer's *Iliad* and *Odyssey*.

## Project structure

### `sources/raw`

The original source texts studied for this project: the *Iliad* (`iliad.txt`) and the *Odyssey* (`odyssey.txt`), in Samuel Butler's English prose translation. Each file is divided into 24 books, marked by `BOOK I` through `BOOK XXIV`. Note that this translation uses Roman names for the gods (e.g. Jove for Zeus, Minerva for Athena) and calls Odysseus "Ulysses."

### `templates`

Markdown templates that define the structure for each type of knowledge-base entry. In addition to the YAML frontmatter, each template renders its metadata as an infobox table under the title (rows like `| **Kind** | ... |`) so the key facts are visible in the rendered Markdown, not just in the frontmatter.

- `CHARACTER.md` — the template used for every file in `waiki/character`: frontmatter (`Name`, `Kind`, `Origin`, `Gender`, `AfiliatedTo`) followed by `Appearances`, `Personality`, and `Entourage` sections.
- `LOCATION.md` — the template used for location entries: frontmatter (`Name`, `Kind`, `Region`, `Ruler`, `AfiliatedTo`) followed by `Appearances`, `Significance`, and `Inhabitants` sections. The `Ruler` field must be a Markdown link to an existing character file in `waiki/character`, written as `[filename](../character/filename.md)` (e.g. `[priam](../character/priam.md)`) — not a plain name.

### `waiki/character`

One Markdown file per character appearing in the *Iliad* and/or the *Odyssey*, built from the template above. Each file gives a short description of the character, the books in which they appear, three personality traits backed by direct quotations from the source text, and three characters forming their entourage. Covers gods, Achaean and Trojan heroes, Trojan War women, the Ithacan household, and the divine and monstrous figures Odysseus encounters on his journey.

### `waiki/location`

One Markdown file per location appearing in the *Iliad* and/or the *Odyssey*, built from `templates/LOCATION.md`. Each file gives a short description of the place, the books in which it appears, three notable features or events backed by direct quotations from the source text, and three characters associated with it. Covers cities (Troy, Pylos, Sparta, Mycenae), islands (Ithaca, Scheria, Ogygia, Aeaea, Aeolia), and divine realms (Mount Olympus, the House of Hades).

### `verif`

A template conformance checker for the `waiki` entries. `verif/verify.py` reads a template in `templates/` and derives the rules a conforming entry must satisfy, then checks entries against them — it is template-driven, so it follows any change to the templates. It verifies that (1) every frontmatter key is present and filled, (2) the infobox values match the frontmatter, (3) all required `##` sections exist, and (4) every Markdown link into `../character/` points to an existing character file.

```bash
python3 verif/verify.py                    # check every entry in waiki/
python3 verif/verify.py waiki/location/troy.md   # check specific files
```

Exit code is `0` if all checked files conform, `1` otherwise (suitable for a pre-commit hook or CI step). No third-party dependencies — standard-library Python 3 only. See `verif/README.md` for details.
