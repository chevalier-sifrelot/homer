#!/usr/bin/env python3
"""Verify that waiki entries conform to their Markdown template.

The checker has two layers.

TEMPLATE CONFORMANCE (always run) is *template-driven*: it reads a template file
(e.g. templates/CHARACTER.md) and derives the rules a conforming entry must
satisfy:

  1. Frontmatter — every key declared in the template's frontmatter must be
     present, non-empty, and not left as the template's placeholder text.
  2. Infobox — the metadata table under the title (rows like
     `| **Kind** | {{Kind}} |`) must be present, and each displayed value must
     match the corresponding frontmatter value.
  3. Sections — every `## Heading` in the template must exist in the entry.
  4. Wikilinks — any frontmatter value written as `[[name]]` must point to an
     existing character file in `waiki/character/name.md`.

CONTENT CONFORMANCE (--content) checks the quotations against the source texts
in sources/raw/. The rule is deliberately narrow and stated in terms of *words*:

  * Formatting is ignored, because it is an artefact of how the quote is written
    down rather than a difference in the text: line wrapping and whitespace (the
    Butler prose wraps mid-sentence), the shape of quotation marks (a quote
    delimited by `"` cannot nest a literal `"`), letter case, and punctuation.
  * Words are not negotiable. A word added, removed or altered fails. The only
    permitted omission is one made explicit with `...`, and the fragments either
    side of it must occur in that order within the cited book.
  * The citation must name the book the words actually come from.

Usage:
    python3 verify.py                     # template conformance, all entries
    python3 verify.py --content           # template + quotation conformance
    python3 verify.py <file> [<file>...]  # verify specific files
    python3 verify.py --template templates/LOCATION.md <file>...
    python3 verify.py --content --format=github   # GitHub Actions annotations
    python3 verify.py --content --strict  # warnings count as failures

Exit code is 0 if all checked files pass, 1 otherwise.
"""
import argparse
import bisect
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Which template governs which waiki subfolder.
FOLDER_TEMPLATE = {
    "character": "templates/CHARACTER.md",
    "location": "templates/LOCATION.md",
}

# The source texts quotations are checked against, keyed by the name used in
# citations, e.g. "(Iliad, Book VI)".
SOURCES = {
    "Iliad": "sources/raw/iliad.txt",
    "Odyssey": "sources/raw/odyssey.txt",
}

FM_LINE = re.compile(r'^\s*([A-Za-z][\w]*)\s*:\s*(.*?)\s*$')
INFOBOX_TPL_ROW = re.compile(r'^\|\s*\*\*(.+?)\*\*\s*\|\s*\{\{(\w+)\}\}\s*\|\s*$')
INFOBOX_ROW = re.compile(r'^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*$')
SECTION = re.compile(r'^##\s+(.+?)\s*$')
WIKILINK = re.compile(r'\[\[([^\]]+)\]\]')
MDLINK = re.compile(r'\[[^\]]+\]\(([^)]+)\)')

# A quotation is a run of text between double quotes on a single line.
QUOTED = re.compile(r'"([^"\n]+)"')
# `...` (or a real ellipsis) marks an omission inside a quotation.
ELLIPSIS = re.compile(r'\.\.\.|…')
# e.g. "(Iliad, Book VI)" or "(Odyssey, Books XI)"
CITATION = re.compile(r'\((Iliad|Odyssey),\s*Books?\s+([IVXLCDM]+)\)')
BOOK_MARK = re.compile(r'^BOOK ([IVXLCDM]+)\s*$', re.MULTILINE)
# A word is a run of letters/digits, optionally joined by inner apostrophes
# ("priest's"). A leading or trailing quote mark is punctuation, not part of it.
WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*")

# A single quoted word reads as emphasis rather than a quotation, so it is not
# checked against the sources.
MIN_QUOTE_WORDS = 2


def normalise_word(w):
    return w.replace('’', "'").lower()


def words_of(text):
    """The sequence of words in a string, formatting discarded."""
    return [normalise_word(m.group(0)) for m in WORD.finditer(text)]


def roman_value(r):
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    total = 0
    for i, c in enumerate(r):
        v = values[c]
        if i + 1 < len(r) and values[r[i + 1]] > v:
            total -= v
        else:
            total += v
    return total


def strip_quotes(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v.strip()


def split_frontmatter(text):
    """Return (frontmatter_dict, body_str). Raises ValueError if no frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---' frontmatter delimiter")
    fm = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        m = FM_LINE.match(lines[i])
        if m:
            fm[m.group(1)] = strip_quotes(m.group(2))
        i += 1
    if i >= len(lines):
        raise ValueError("missing closing '---' frontmatter delimiter")
    body = "\n".join(lines[i + 1:])
    return fm, body, i + 2  # 1-based line number of the first body line


def parse_template(path):
    """Extract the rules a conforming entry must satisfy from a template file."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm, body, _ = split_frontmatter(text)
    infobox = []  # list of (label, frontmatter_key)
    sections = []
    for line in body.splitlines():
        m = INFOBOX_TPL_ROW.match(line)
        if m:
            infobox.append((m.group(1), m.group(2)))
            continue
        m = SECTION.match(line)
        if m:
            sections.append(m.group(1))
    return {
        "keys": list(fm.keys()),
        "placeholders": fm,          # key -> placeholder value
        "infobox": infobox,
        "sections": sections,
    }


def parse_infobox(body):
    """Return {label: value} for the metadata table rows found in an entry body.

    Only rows whose value is not a template placeholder ({{...}}) are kept.
    """
    rows = {}
    for line in body.splitlines():
        m = INFOBOX_ROW.match(line)
        if not m:
            continue
        label, value = m.group(1).strip(), m.group(2).strip()
        if value == "---" or set(value) == {"-"}:
            continue  # separator row
        if "{{" in value:
            continue
        rows[label] = value
    return rows


# --------------------------------------------------------------------------- #
# Source texts
# --------------------------------------------------------------------------- #

class Source:
    """A source text indexed as a sequence of words, with book boundaries.

    Quotations are matched as word sequences, so every difference of whitespace,
    quotation-mark shape, case and punctuation is invisible here by construction
    rather than by a list of exceptions.
    """

    def __init__(self, name, path):
        self.name = name
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()

        matches = list(WORD.finditer(text))
        self.words = [normalise_word(m.group(0)) for m in matches]
        self.offsets = [m.start() for m in matches]

        # Character offset at which each book starts, in reading order.
        self.book_starts = []
        self.book_names = []
        for m in BOOK_MARK.finditer(text):
            self.book_starts.append(m.start())
            self.book_names.append(m.group(1))

        # First word -> positions, so a lookup does not scan the whole text.
        self.first_word = {}
        for i, w in enumerate(self.words):
            self.first_word.setdefault(w, []).append(i)

    def book_of(self, word_index):
        """The book containing the word at `word_index`, or None."""
        offset = self.offsets[word_index]
        i = bisect.bisect_right(self.book_starts, offset) - 1
        return self.book_names[i] if i >= 0 else None

    def occurrences(self, seq, start=0):
        """Word indices where the word sequence `seq` occurs, at or after `start`."""
        if not seq:
            return
        n = len(seq)
        for i in self.first_word.get(seq[0], ()):
            if i < start:
                continue
            if self.words[i:i + n] == seq:
                yield i

    def best_alignment(self, seq, book=None):
        """(matched, position) for the occurrence of seq[0] that matches furthest.

        Reporting the alignment that runs longest — rather than the first one
        found — is what makes the diagnostic point at the real divergence
        instead of at an unrelated occurrence of the opening word.
        """
        best, best_pos = 0, None
        for i in self.first_word.get(seq[0], ()):
            if book is not None and self.book_of(i) != book:
                continue
            n = 0
            while n < len(seq) and i + n < len(self.words) and self.words[i + n] == seq[n]:
                n += 1
            if n > best:
                best, best_pos = n, i
                if n == len(seq):
                    break
        return best, best_pos

    def context(self, word_index, count):
        return " ".join(self.words[word_index:word_index + count])


def load_sources():
    sources = {}
    for name, rel in SOURCES.items():
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.isfile(path):
            raise SystemExit(f"missing source text: {rel}")
        sources[name] = Source(name, path)
    return sources


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

def verify_template(path, rules):
    """Return a list of (line, message) for template conformance."""
    errors = []
    with open(path, encoding="utf-8") as f:
        text = f.read()

    try:
        fm, body, _ = split_frontmatter(text)
    except ValueError as e:
        return [(1, str(e))]

    # 1. Frontmatter keys present, filled, not placeholder.
    for key in rules["keys"]:
        if key not in fm:
            errors.append((1, f"frontmatter missing key '{key}'"))
        elif fm[key] == "":
            errors.append((1, f"frontmatter key '{key}' is empty"))
        elif fm[key] == rules["placeholders"].get(key):
            errors.append((1, f"frontmatter key '{key}' still holds the template placeholder"))

    # 2. Infobox present and consistent with frontmatter.
    infobox = parse_infobox(body)
    for label, key in rules["infobox"]:
        if label not in infobox:
            errors.append((1, f"infobox missing row '**{label}**'"))
            continue
        expected = fm.get(key, "")
        if infobox[label] != expected:
            errors.append((
                1,
                f"infobox '**{label}**' shows '{infobox[label]}' "
                f"but frontmatter '{key}' is '{expected}'",
            ))

    # 3. Required sections present.
    body_sections = set()
    for line in body.splitlines():
        m = SECTION.match(line)
        if m:
            body_sections.add(m.group(1))
    for sec in rules["sections"]:
        if sec not in body_sections:
            errors.append((1, f"missing section '## {sec}'"))

    # 4. Reference targets exist. Markdown links are resolved relative to the
    #    entry's own directory; wikilinks resolve to waiki/character/<name>.md.
    entry_dir = os.path.dirname(os.path.abspath(path))
    for key, value in fm.items():
        for rel in MDLINK.findall(value):
            target_path = os.path.normpath(os.path.join(entry_dir, rel))
            if not os.path.isfile(target_path):
                errors.append((
                    1,
                    f"frontmatter '{key}' links to '{rel}' but that file does not exist",
                ))
        for target in WIKILINK.findall(value):
            target_path = os.path.join(REPO_ROOT, "waiki", "character", target + ".md")
            if not os.path.isfile(target_path):
                errors.append((
                    1,
                    f"frontmatter '{key}' links to [[{target}]] "
                    f"but waiki/character/{target}.md does not exist",
                ))

    return errors


def check_quotation(quote, work, book, sources):
    """Check one quotation. Return (severity, message) or None if it conforms.

    `work` and `book` come from the citation and may be None when the quotation
    carries none.
    """
    fragments = [words_of(f) for f in ELLIPSIS.split(quote)]
    fragments = [f for f in fragments if f]
    if not fragments:
        return None
    if sum(len(f) for f in fragments) < MIN_QUOTE_WORDS:
        return None  # emphasis, not a quotation

    if work is None:
        # No citation: the words must still exist somewhere in the corpus.
        for candidate in sources.values():
            if _fragments_in_order(candidate, fragments, None) is not None:
                return ("warning", "quotation carries no '(Iliad|Odyssey, Book N)' citation")
        return ("error", _explain_missing(quote, fragments, sources))

    source = sources[work]
    if _fragments_in_order(source, fragments, book) is not None:
        return None

    # The words are not in the cited book. Say precisely what is wrong.
    if _fragments_in_order(source, fragments, None) is not None:
        found = sorted(
            {source.book_of(i) for i in source.occurrences(fragments[0])},
            key=lambda b: roman_value(b) if b else 0,
        )
        return (
            "error",
            f"cited {work} Book {book} but these words are in "
            f"{work} Book {'/'.join(b for b in found if b)}",
        )
    for other_name, other in sources.items():
        if other_name == work:
            continue
        pos = _fragments_in_order(other, fragments, None)
        if pos is not None:
            return (
                "error",
                f"cited {work} Book {book} but these words are in the "
                f"{other_name}, Book {other.book_of(pos)}",
            )
    return ("error", _explain_missing(quote, fragments, sources, work, book))


def _fragments_in_order(source, fragments, book):
    """First word index of fragment 0 if every fragment occurs in order.

    When `book` is given, every fragment must sit inside that book. Returns None
    if the sequence cannot be satisfied.
    """
    for first in source.occurrences(fragments[0]):
        if book is not None and source.book_of(first) != book:
            continue
        pos = first + len(fragments[0])
        ok = True
        for frag in fragments[1:]:
            nxt = None
            for i in source.occurrences(frag, pos):
                if book is not None and source.book_of(i) != book:
                    continue
                nxt = i
                break
            if nxt is None:
                ok = False
                break
            pos = nxt + len(frag)
        if ok:
            return first
    return None


def _explain_missing(quote, fragments, sources, work=None, book=None):
    """Explain the first fragment that cannot be found, and where it diverges.

    When the entry carries a citation, the explanation is anchored in the book it
    names, so the report answers "what does the cited book actually say here?".
    """
    scope = [sources[work]] if work else list(sources.values())
    for frag in fragments:
        if any(next((i for i in src.occurrences(frag)
                     if book is None or src.book_of(i) == book), None) is not None
               for src in scope):
            continue  # this fragment is fine; the failure is elsewhere
        # Locate the source passage that follows this fragment the longest.
        best = (0, None, None)  # matched words, source, position
        for source in scope:
            k, pos = source.best_alignment(frag, book)
            if k > best[0]:
                best = (k, source, pos)
        k, source, pos = best
        if not k or source is None or pos is None:
            return "quotation not found in the source texts"
        expected = source.context(pos + k, 4)
        got = " ".join(frag[k:k + 4]) or "(nothing further)"
        return (
            f"diverges from the source after {k} word(s) "
            f"(in the {source.name}, Book {source.book_of(pos)}): "
            f'source has "...{expected}", entry has "...{got}"'
        )
    return "quotation fragments do not occur in this order in the cited book"


def verify_content(path, sources):
    """Return a list of (line, severity, message) for quotation conformance."""
    problems = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        _, _, body_start = split_frontmatter(text)
    except ValueError:
        return problems  # already reported by the template layer

    lines = text.splitlines()
    for offset, line in enumerate(lines[body_start - 1:]):
        lineno = body_start + offset
        if line.startswith("|"):
            continue  # infobox row
        citation = CITATION.search(line)
        work = citation.group(1) if citation else None
        book = citation.group(2) if citation else None
        for quote in QUOTED.findall(line):
            result = check_quotation(quote, work, book, sources)
            if result is None:
                continue
            severity, message = result
            excerpt = " ".join(quote.split())
            if len(excerpt) > 70:
                excerpt = excerpt[:70] + "..."
            problems.append((lineno, severity, f'{message} — "{excerpt}"'))
    return problems


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def template_for(path):
    """Pick the template governing a file, based on its parent folder name."""
    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    rel = FOLDER_TEMPLATE.get(folder)
    if rel is None:
        return None
    return os.path.join(REPO_ROOT, rel)


def collect_default_files():
    files = []
    for folder in FOLDER_TEMPLATE:
        d = os.path.join(REPO_ROOT, "waiki", folder)
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if name.endswith(".md"):
                    files.append(os.path.join(d, name))
    return files


def emit(fmt, severity, rel, lineno, message):
    if fmt == "github":
        kind = "error" if severity == "error" else "warning"
        print(f"::{kind} file={rel},line={lineno}::{message}")
    else:
        print(f"     - {severity}: {message}")


def main():
    ap = argparse.ArgumentParser(description="Verify waiki entries against their template.")
    ap.add_argument("files", nargs="*", help="Markdown files to check (default: all of waiki/).")
    ap.add_argument("--template", help="Force a specific template for all given files.")
    ap.add_argument("--content", action="store_true",
                    help="Also check quotations verbatim against sources/raw/.")
    ap.add_argument("--strict", action="store_true",
                    help="Treat warnings as failures.")
    ap.add_argument("--format", choices=("text", "github"), default="text",
                    help="Output format ('github' emits workflow annotations).")
    args = ap.parse_args()

    files = args.files or collect_default_files()
    if not files:
        print("No files to check.")
        return 0

    forced_rules = parse_template(args.template) if args.template else None
    template_cache = {}
    sources = load_sources() if args.content else None

    n_errors = n_warnings = n_bad_files = 0

    for path in files:
        if forced_rules is not None:
            rules = forced_rules
        else:
            tpl = template_for(path)
            if tpl is None:
                print(f"SKIP {path}: no template known for this folder")
                continue
            if tpl not in template_cache:
                template_cache[tpl] = parse_template(tpl)
            rules = template_cache[tpl]

        rel = os.path.relpath(path, REPO_ROOT)
        problems = [(line, "error", msg) for line, msg in verify_template(path, rules)]
        if args.content:
            problems += verify_content(path, sources)
        problems.sort(key=lambda p: p[0])

        errors = [p for p in problems if p[1] == "error"]
        warnings = [p for p in problems if p[1] == "warning"]
        n_errors += len(errors)
        n_warnings += len(warnings)

        if problems:
            if errors:
                n_bad_files += 1
            if args.format != "github":
                print(f"{'FAIL' if errors else 'WARN'} {rel}")
            for lineno, severity, message in problems:
                emit(args.format, severity, rel, lineno, message)
        elif args.format != "github":
            print(f"OK   {rel}")

    print()
    summary = f"{n_errors} error(s), {n_warnings} warning(s) across {len(files)} file(s)."
    print(summary)
    if n_errors:
        print(f"{n_bad_files} file(s) need fixing.")
        return 1
    if n_warnings and args.strict:
        print("Warnings are failures under --strict.")
        return 1
    print("All checked files conform.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
