# Homer

A Markdown knowledge base on Ancient Greek mythology, built from a close study of Homer's *Iliad* and *Odyssey*.

## Project structure

### `sources/raw`

The original source texts studied for this project: the *Iliad* (`iliad.txt`) and the *Odyssey* (`odyssey.txt`), in Samuel Butler's English prose translation. Each file is divided into 24 books, marked by `BOOK I` through `BOOK XXIV`. Note that this translation uses Roman names for the gods (e.g. Jove for Zeus, Minerva for Athena) and calls Odysseus "Ulysses."

### `templates`

Markdown templates that define the structure for each type of knowledge-base entry.

- `CHARACTER.md` — the template used for every file in `waiki/character`: frontmatter (`Name`, `Kind`, `Origin`, `Gender`, `AfiliatedTo`) followed by `Appearances`, `Personality`, and `Entourage` sections.

### `waiki/character`

One Markdown file per character appearing in the *Iliad* and/or the *Odyssey*, built from the template above. Each file gives a short description of the character, the books in which they appear, three personality traits backed by direct quotations from the source text, and three characters forming their entourage. Covers gods, Achaean and Trojan heroes, Trojan War women, the Ithacan household, and the divine and monstrous figures Odysseus encounters on his journey.
