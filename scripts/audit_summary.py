#!/usr/bin/env python3
"""The audit's items, without reading the audit.

`open-items.md` is 400-odd lines of Markdown and `decisions.md` is another 350. A question like
"which items are open on `import std;`" does not need either of them read in full.

This script reads the machine-readable registry instead and prints the slice that was asked for.

    scripts/audit_summary.py                     # the open items, one line each
    scripts/audit_summary.py --prefix MOD        # one prefix
    scripts/audit_summary.py --owner             # the owner's decisions
    scripts/audit_summary.py --category compile  # everything a compile settles
    scripts/audit_summary.py --state answered    # the answered and contingent items
    scripts/audit_summary.py --id MOD-11         # one item, in full
    scripts/audit_summary.py --counts            # the counts only

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO_ROOT / "docs" / "cxx26-features-audit" / "audit-index.json"


def load_index() -> dict:
    if not INDEX_PATH.exists():
        print(
            f"missing {INDEX_PATH.relative_to(REPO_ROOT)} - run `mise run audit:index`",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def format_item(item: dict, detail: bool = False) -> str:
    prefix = f"{item['id']:<9}"
    if detail:
        lines = [
            f"{item['id']} - {item['title']}",
            f"    kind      {item['kind']}",
            f"    category  {item['category']}",
            f"    state     {item['state']}",
            f"    settled by {item.get('settled_by', '')}",
            f"    section   {item.get('section_title', '')}",
            f"    document  {item.get('doc', '')}",
        ]
        if item.get("evidence"):
            lines.append(f"    evidence  {item['evidence']}")
        return "\n".join(lines)
    title = item["title"]
    if len(title) > 90:
        title = title[:89] + "…"
    return f"  {prefix} [{item['category']:<20}] {title}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--prefix", help="only this prefix, e.g. MOD")
    parser.add_argument(
        "--owner", action="store_true", help="only the owner's decisions"
    )
    parser.add_argument("--category", help="only this category, e.g. compile")
    parser.add_argument("--state", help="only this state: open, answered, contingent")
    parser.add_argument("--id", dest="item_id", help="one item, in full")
    parser.add_argument("--counts", action="store_true", help="the counts only")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    index = load_index()
    items = index["items"] + index["answered_items"]

    if args.item_id:
        wanted = args.item_id.upper()
        found = [item for item in items if item["id"] == wanted]
        if not found:
            print(f"no item {wanted}", file=sys.stderr)
            return 1
        for item in found:
            print(format_item(item, detail=True))
        return 0

    if args.counts:
        counts = index["counts"]
        print(json.dumps(counts, indent=2, sort_keys=True))
        return 0

    selected = []
    for item in items:
        if args.prefix and not item["id"].startswith(args.prefix.upper() + "-"):
            continue
        if args.owner and item["category"] != "owner-decision":
            continue
        if args.category and item["category"] != args.category:
            continue
        if args.state and item["state"] != args.state:
            continue
        selected.append(item)

    if args.json:
        print(json.dumps(selected, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    if not selected:
        print("nothing matched")
        return 0

    print(f"{len(selected)} item(s)\n")
    for item in selected:
        print(format_item(item))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
