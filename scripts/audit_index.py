#!/usr/bin/env python3
"""The audit's item registry - derived from the Markdown, never authored.

`docs/cxx26-features-audit/open-items.md` is the source of truth for the audit's items. This
module parses it and produces `docs/cxx26-features-audit/audit-index.json`, a machine-readable
registry that other tools read instead of re-parsing Markdown.

The registry is a *derived artifact*. It is committed so that a tool can read it cheaply, and
`scripts/verify_audit.py` fails when the committed copy is stale. Never edit the JSON by hand;
run `mise run audit:index`.

Stdlib only. No compiler, no CMake, no network.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OPEN_ITEMS = REPO_ROOT / "docs" / "cxx26-features-audit" / "open-items.md"
AUDIT_README = REPO_ROOT / "docs" / "cxx26-features-audit" / "README.md"
INDEX_PATH = REPO_ROOT / "docs" / "cxx26-features-audit" / "audit-index.json"

SECTION_RE = re.compile(r"^## (\d+)\.\s+(.*)$")
DEF_RE = re.compile(r"^###\s+(DEF-\d+)\s+-\s+(.*)$")
ROW_RE = re.compile(r"^\|\s*([A-Z]+-\d+)\s*\|")
DATE_RE = re.compile(r"^\*\*Date:\*\*\s*(.*)$")

# The sections whose tables hold *open* items, and the sections that hold the rest.
OPEN_SECTIONS = range(2, 12)
ANSWERED_SECTION = 13


def slugify(text: str) -> str:
    """GitHub's heading anchor rules, close enough for a link check."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text.strip("-")


def split_row(line: str) -> list[str]:
    """Split a Markdown table row into its cells, dropping the empty ends."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def classify(settled_by: str) -> str:
    """The kind of measurement that settles an item.

    The wording in the Markdown is prose, so this maps the phrases that are actually used onto a
    fixed vocabulary. The order matters: "a build-system change, then a run" is a build-system
    change, and "reading ... (done) plus a compile" is a compile.
    """
    text = settled_by.lower()
    if "owner decision" in text:
        return "owner-decision"
    if "a decision now" in text:
        return "decided"
    if "build-system change" in text:
        return "build-system-change"
    if "compile" in text or "scratch translation unit" in text:
        return "compile"
    if "run" in text:
        return "run"
    if "preprocessor" in text:
        return "preprocessor"
    if "reading" in text:
        return "reading"
    return "other"


def short_title(text: str, limit: int = 140) -> str:
    """A one-line summary of a question, for the registry and for summaries."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "..."


def kind_for(item_id: str) -> str:
    prefix = item_id.rsplit("-", 1)[0]
    if prefix == "DEF":
        return "defect"
    if prefix == "COV":
        return "work-item"
    return "question"


# Owner decision IDs that don't follow the prefix rule
OWNER_DECISION_IDS = {
    "FMT-14", "QUIL-9", "TOOL-13", "TOOL-14",
    "BUILD-1", "BUILD-2", "BUILD-3", "BUILD-4", "BUILD-5",
    "BUILD-7", "BUILD-8", "BUILD-9", "ENV-2", "ENV-3",
}

# Items that are BUILD prefix but NOT owner decisions
NON_OWNER_BUILD_IDS = {"BUILD-6"}

def category_for(item_id: str) -> str:
    """Infer the audit category from the item ID prefix."""
    if item_id in OWNER_DECISION_IDS:
        return "owner-decision"
    if item_id in NON_OWNER_BUILD_IDS:
        return "reading"
    prefix = item_id.rsplit("-", 1)[0]
    if prefix == "DEF":
        return "fix-and-test"
    if prefix == "COV":
        return "test"
    if prefix in ("FMT", "QUIL", "MOD", "REFL", "MAC", "TOOL"):
        return "compile"
    if prefix == "BUILD":
        return "owner-decision"
    if prefix == "ENV":
        return "owner-decision"
    if prefix == "VCPKG":
        return "reading"
    if prefix == "TOOL":
        return "compile"
    return "other"


def parse_open_items(path: Path = OPEN_ITEMS) -> dict:
    """Parse the open-items table into the registry's shape."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    source_date = ""
    for line in lines[:10]:
        match = DATE_RE.match(line)
        if match:
            source_date = match.group(1).strip()
            break

    items: list[dict] = []
    section = 0
    section_title = ""
    section_anchor = ""
    defects: dict[str, dict] = {}
    answered: list[dict] = []

    for line in lines:
        section_match = SECTION_RE.match(line)
        if section_match:
            section = int(section_match.group(1))
            section_title = section_match.group(2).strip()
            section_anchor = f"{section}-{slugify(section_title)}"
            continue

        defect_match = DEF_RE.match(line)
        if defect_match:
            item_id = defect_match.group(1)
            defects[item_id] = {
                "id": item_id,
                "title": short_title(defect_match.group(2)),
                "kind": "defect",
                "category": "fix-and-test",
                "state": "open",
                "section": 1,
                "section_title": "The issues - known defects, to fix",
                "doc": f"docs/cxx26-features-audit/open-items.md#{section_anchor}",
                "settled_by": "a fix and a test",
            }
            continue

        if not line.startswith("|"):
            continue

        cells = split_row(line)
        if len(cells) < 2:
            continue
        item_id = cells[0]
        if not re.fullmatch(r"[A-Z]+-\d+", item_id):
            continue

        if section in OPEN_SECTIONS:
            if len(cells) < 3:
                continue
            question, settled_by = cells[1], cells[2]
            if item_id.startswith("COV-"):
                # A coverage to-do is work, not a question: its third column says where the
                # uncovered branch is, not what would settle it.
                category, settled_by = "test", "a test"
            else:
                category = classify(settled_by)
            items.append(
                {
                    "id": item_id,
                    "title": short_title(question),
                    "kind": kind_for(item_id),
                    "category": category,
                    "state": "open",
                    "section": section,
                    "section_title": section_title,
                    "doc": f"docs/cxx26-features-audit/open-items.md#{section_anchor}",
                    "settled_by": settled_by,
                }
            )
        elif section == ANSWERED_SECTION:
            if len(cells) < 5:
                continue
            question, state, answer, evidence = cells[1], cells[2], cells[3], cells[4]
            state_value = "contingent" if state.lower().startswith("contingent") else "answered"
            answered.append(
                {
                    "id": item_id,
                    "title": short_title(question),
                    "kind": kind_for(item_id),
                    "category": category_for(item_id),
                    "state": state_value,
                    "section": section,
                    "section_title": section_title,
                    "doc": f"docs/cxx26-features-audit/open-items.md#{section_anchor}",
                    "settled_by": answer,
                    "evidence": evidence,
                }
            )

    items = list(defects.values()) + items
    items.sort(key=lambda item: item["id"])
    answered.sort(key=lambda item: item["id"])

    counts = {
        "open": sum(1 for item in items if item["state"] == "open"),
        "answered": sum(1 for item in answered if item["state"] == "answered"),
        "contingent": sum(1 for item in answered if item["state"] == "contingent"),
        "by_category": tally(item["category"] for item in items),
        "by_prefix": tally(item["id"].rsplit("-", 1)[0] for item in items),
        "by_kind": tally(item["kind"] for item in items),
    }

    return {
        "schema": 1,
        "generated_by": "scripts/audit_index.py",
        "source": "docs/cxx26-features-audit/open-items.md",
        "source_date": source_date,
        "counts": counts,
        "items": items,
        "answered_items": answered,
    }


def tally(values) -> dict:
    out: dict[str, int] = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items()))


def parse_parts(path: Path = AUDIT_README) -> list[dict]:
    """The audit's parts table: the number, the file and the subject.

    Only the table under "## The parts" is read - the README has other tables whose first column
    is a number too.
    """
    parts = []
    in_parts = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("## "):
            in_parts = line.strip().lower() == "## the parts"
            continue
        if not in_parts or not line.startswith("|"):
            continue
        cells = split_row(line)
        if len(cells) < 3 or not cells[0].isdigit():
            continue
        number = int(cells[0])
        match = re.search(r"\(([^)]+)\)", cells[1])
        parts.append(
            {
                "part": number,
                "file": match.group(1) if match else cells[1],
                "subject": short_title(cells[2], 120),
            }
        )
    return parts


def build_index(path: Path = OPEN_ITEMS) -> dict:
    index = parse_open_items(path)
    index["parts"] = parse_parts()
    return index


def render(index: dict) -> str:
    return json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the registry (the default is to print it)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the committed registry is stale",
    )
    args = parser.parse_args(argv)

    index = build_index()
    rendered = render(index)

    if args.check:
        if not INDEX_PATH.exists():
            print(f"missing: {INDEX_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        if INDEX_PATH.read_text(encoding="utf-8") != rendered:
            print(
                f"stale: {INDEX_PATH.relative_to(REPO_ROOT)} - run `mise run audit:index`",
                file=sys.stderr,
            )
            return 1
        print("the registry is up to date")
        return 0

    if args.write:
        INDEX_PATH.write_text(rendered, encoding="utf-8")
        print(f"wrote {INDEX_PATH.relative_to(REPO_ROOT)}")
        print(
            f"  {index['counts']['open']} open, "
            f"{index['counts']['answered']} answered, "
            f"{index['counts']['contingent']} contingent"
        )
        return 0

    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
