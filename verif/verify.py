#!/usr/bin/env python3
"""Verify that waiki entries conform to their Markdown template.

The checker is *template-driven*: it reads a template file (e.g.
templates/CHARACTER.md) and derives the rules a conforming entry must satisfy:

  1. Frontmatter — every key declared in the template's frontmatter must be
     present, non-empty, and not left as the template's placeholder text.
  2. Infobox — the metadata table under the title (rows like
     `| **Kind** | {{Kind}} |`) must be present, and each displayed value must
     match the corresponding frontmatter value.
  3. Sections — every `## Heading` in the template must exist in the entry.
  4. Wikilinks — any frontmatter value written as `[[name]]` must point to an
     existing character file in `waiki/character/name.md`.

Usage:
    python3 verify.py                     # verify every entry in waiki/
    python3 verify.py <file> [<file>...]  # verify specific files
    python3 verify.py --template templates/LOCATION.md <file>...

Exit code is 0 if all checked files pass, 1 otherwise.
"""
import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Which template governs which waiki subfolder.
FOLDER_TEMPLATE = {
    "character": "templates/CHARACTER.md",
    "location": "templates/LOCATION.md",
}

FM_LINE = re.compile(r'^\s*([A-Za-z][\w]*)\s*:\s*(.*?)\s*$')
INFOBOX_TPL_ROW = re.compile(r'^\|\s*\*\*(.+?)\*\*\s*\|\s*\{\{(\w+)\}\}\s*\|\s*$')
INFOBOX_ROW = re.compile(r'^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*$')
SECTION = re.compile(r'^##\s+(.+?)\s*$')
WIKILINK = re.compile(r'\[\[([^\]]+)\]\]')
MDLINK = re.compile(r'\[[^\]]+\]\(([^)]+)\)')


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
    return fm, body


def parse_template(path):
    """Extract the rules a conforming entry must satisfy from a template file."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm, body = split_frontmatter(text)
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


def verify_file(path, rules):
    """Return a list of error strings (empty == conforms)."""
    errors = []
    with open(path, encoding="utf-8") as f:
        text = f.read()

    try:
        fm, body = split_frontmatter(text)
    except ValueError as e:
        return [str(e)]

    # 1. Frontmatter keys present, filled, not placeholder.
    for key in rules["keys"]:
        if key not in fm:
            errors.append(f"frontmatter missing key '{key}'")
        elif fm[key] == "":
            errors.append(f"frontmatter key '{key}' is empty")
        elif fm[key] == rules["placeholders"].get(key):
            errors.append(f"frontmatter key '{key}' still holds the template placeholder")

    # 2. Infobox present and consistent with frontmatter.
    infobox = parse_infobox(body)
    for label, key in rules["infobox"]:
        if label not in infobox:
            errors.append(f"infobox missing row '**{label}**'")
            continue
        expected = fm.get(key, "")
        if infobox[label] != expected:
            errors.append(
                f"infobox '**{label}**' shows '{infobox[label]}' "
                f"but frontmatter '{key}' is '{expected}'"
            )

    # 3. Required sections present.
    body_sections = set()
    for line in body.splitlines():
        m = SECTION.match(line)
        if m:
            body_sections.add(m.group(1))
    for sec in rules["sections"]:
        if sec not in body_sections:
            errors.append(f"missing section '## {sec}'")

    # 4. Reference targets exist. Markdown links are resolved relative to the
    #    entry's own directory; wikilinks resolve to waiki/character/<name>.md.
    entry_dir = os.path.dirname(os.path.abspath(path))
    for key, value in fm.items():
        for rel in MDLINK.findall(value):
            target_path = os.path.normpath(os.path.join(entry_dir, rel))
            if not os.path.isfile(target_path):
                errors.append(
                    f"frontmatter '{key}' links to '{rel}' "
                    f"but that file does not exist"
                )
        for target in WIKILINK.findall(value):
            target_path = os.path.join(REPO_ROOT, "waiki", "character", target + ".md")
            if not os.path.isfile(target_path):
                errors.append(
                    f"frontmatter '{key}' links to [[{target}]] "
                    f"but waiki/character/{target}.md does not exist"
                )

    return errors


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


def main():
    ap = argparse.ArgumentParser(description="Verify waiki entries against their template.")
    ap.add_argument("files", nargs="*", help="Markdown files to check (default: all of waiki/).")
    ap.add_argument("--template", help="Force a specific template for all given files.")
    args = ap.parse_args()

    files = args.files or collect_default_files()
    if not files:
        print("No files to check.")
        return 0

    forced_rules = parse_template(args.template) if args.template else None
    template_cache = {}
    total_errors = 0

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

        errors = verify_file(path, rules)
        rel = os.path.relpath(path, REPO_ROOT)
        if errors:
            total_errors += len(errors)
            print(f"FAIL {rel}")
            for e in errors:
                print(f"     - {e}")
        else:
            print(f"OK   {rel}")

    print()
    if total_errors:
        print(f"{total_errors} problem(s) found.")
        return 1
    print("All checked files conform to their template.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
