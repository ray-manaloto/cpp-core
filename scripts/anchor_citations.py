#!/usr/bin/env python3
"""The audit's citations, held still.

A citation is a claim about a range of lines: "the scanner is at `format.hpp:220-281`". The
claim is only worth anything while it is true. When the source moves - a reformat, a new
function, a deleted line - the claim does not move with it, and the audit ends up citing
lines that say something else. That is not a hypothetical: 196 of the audit's 291 line
citations were stale after one reformat, and two of them named lines the file did not have.

This records what every cited line says, and checks that it still says it.

    python3 scripts/anchor_citations.py --write     regenerate the baseline
    python3 scripts/anchor_citations.py --check     compare the tree with the baseline
    python3 scripts/anchor_citations.py             report what the baseline holds

THE BASELINE IS DERIVED. Like audit-index.json and measurements.json, it is never hand-edited.
Regenerating it is a deliberate act, and `--write` prints what drifted before it overwrites the
file, so blessing a drift is something you can see you have done.

THE HASH IS WHITESPACE-INSENSITIVE. A re-indent does not change what a line says. Moving a
line does: the content at the cited line number is different, and the hash says so.

Stdlib only. No compiler, no CMake, no network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import citations

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "docs" / "cxx26-features-audit"
BASELINE = AUDIT_DIR / "citations.json"


def line_hash(line: str) -> str:
    """A hash of what a line says, ignoring how it is spaced."""
    normalized = re.sub(r"\s+", "", line)
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def current() -> dict[str, dict[str, str]]:
    """What every cited line says now: a file, and the lines of it that are cited."""
    anchors: dict[str, dict[str, str]] = {}
    for citation in citations.all_citations():
        path = REPO_ROOT / citation.file
        lines = citations.source_lines(path)
        for number in citation.lines:
            if number < 1 or number > len(lines):
                continue
            anchors.setdefault(citation.file, {})[str(number)] = line_hash(
                lines[number - 1]
            )
    return anchors


def current_citations() -> dict[str, list[str]]:
    """Every citation, by the document that makes it.

    The document's own line number is deliberately not part of the record: a paragraph added
    above a citation does not change the claim the citation makes, and the baseline should not
    churn because a document grew.
    """
    grouped: dict[str, list[str]] = {}
    for citation in citations.all_citations():
        span = (
            f"{citation.file}:{citation.start}"
            if citation.start == citation.end
            else f"{citation.file}:{citation.start}-{citation.end}"
        )
        grouped.setdefault(citation.document, []).append(span)
    return {name: sorted(values) for name, values in sorted(grouped.items())}


def render(anchors: dict[str, dict[str, str]]) -> str:
    """The baseline, rendered. The order is fixed, so the diff is readable."""
    payload = {
        "schema": 1,
        "what_this_is": (
            "The audit's claims about the code: every citation it makes, and what every "
            "source line those citations name says. A citation that has drifted off the code "
            "it names is a citation that is wrong, and this is what catches it."
        ),
        "generated_by": "python3 scripts/anchor_citations.py --write",
        "derived_from": "the audit's Markdown documents and the files they cite",
        "citation_count": len(citations.all_citations()),
        "file_count": len(anchors),
        "line_count": sum(len(lines) for lines in anchors.values()),
        "citations": current_citations(),
        "files": {
            name: dict(sorted(lines.items(), key=lambda item: int(item[0])))
            for name, lines in sorted(anchors.items())
        },
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def load() -> dict:
    if not BASELINE.exists():
        return {}
    try:
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def drift_report(before: dict, after: dict) -> list[str]:
    """What changed between two baselines."""
    report: list[str] = []
    old_files = before.get("files", {})
    for name in sorted(set(old_files) | set(after)):
        old_lines = old_files.get(name, {})
        new_lines = after.get(name, {})
        for number in sorted(set(old_lines) | set(new_lines), key=int):
            if number not in old_lines:
                report.append(f"{name}:{number} is newly cited")
            elif number not in new_lines:
                report.append(f"{name}:{number} is no longer cited")
            elif old_lines[number] != new_lines[number]:
                report.append(f"{name}:{number} no longer says what it said")
    return report


def write() -> int:
    """Regenerate the baseline, and say what drifted."""
    before = load()
    anchors = current()
    report = drift_report(before, anchors)
    if report:
        print(f"{len(report)} change(s) since the last baseline:")
        for line in report:
            print(f"  drift: {line}")
    else:
        print("nothing has drifted since the last baseline")
    BASELINE.write_text(render(anchors), encoding="utf-8")
    lines = sum(len(values) for values in anchors.values())
    print(
        f"wrote {BASELINE.relative_to(REPO_ROOT)}: "
        f"{len(citations.all_citations())} citations, {lines} cited lines, {len(anchors)} files"
    )
    return 0


def check() -> int:
    """Compare the tree with the baseline."""
    problems: list[str] = []
    if not BASELINE.exists():
        print(
            f"problem: missing {BASELINE.relative_to(REPO_ROOT)} - run `mise run audit:anchor`"
        )
        return 1
    baseline = load()
    known = baseline.get("files", {})
    all_citations = citations.all_citations()

    for citation in all_citations:
        path = REPO_ROOT / citation.file
        lines = citations.source_lines(path)
        file_known = known.get(citation.file, {})
        for number in citation.lines:
            if number < 1 or number > len(lines):
                problems.append(
                    f"{citation.where} cites {citation.file}:{number}, "
                    f"which the file no longer has"
                )
                continue
            expected = file_known.get(str(number))
            if expected is None:
                problems.append(
                    f"{citation.where} cites {citation.file}:{number}, which the baseline does "
                    f"not know - run `mise run audit:anchor`"
                )
                continue
            if expected != line_hash(lines[number - 1]):
                problems.append(
                    f"{citation.where} cites {citation.file}:{number}, which no longer says "
                    f"what it said"
                )

    cited = citations.audit_citations()[0]
    for name, lines in sorted(known.items()):
        current_lines = cited.get(name, set())
        for number in sorted(int(key) for key in lines):
            if number not in current_lines:
                problems.append(
                    f"{name}:{number} is in the baseline, but no document cites it any more - "
                    f"run `mise run audit:anchor`"
                )

    # The claims themselves: a citation that has moved is a claim that has changed, and the
    # baseline is the record of what the audit claims.
    known_citations = baseline.get("citations", {})
    now_citations = current_citations()
    for document in sorted(set(known_citations) | set(now_citations)):
        before = Counter(known_citations.get(document, []))
        after = Counter(now_citations.get(document, []))
        for span, count in sorted((after - before).items()):
            problems.append(
                f"{document} now cites {span}, which the baseline does not know - "
                f"run `mise run audit:anchor`"
            )
        for span, count in sorted((before - after).items()):
            problems.append(
                f"{document} no longer cites {span} - run `mise run audit:anchor`"
            )

    for problem in problems:
        print(f"problem: {problem}")
    if problems:
        print(f"\n{len(problems)} problem(s)")
        return 1
    print(
        f"the citations hold: {len(all_citations)} citations, "
        f"{sum(len(values) for values in known.values())} cited lines, {len(known)} files"
    )
    return 0


def report() -> int:
    """What the baseline holds."""
    anchors = current()
    lines = sum(len(values) for values in anchors.values())
    print(
        f"{len(citations.all_citations())} citations, {lines} cited lines, {len(anchors)} files"
    )
    for name, values in sorted(anchors.items()):
        print(f"  {name:48s} {len(values):4d} lines")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="regenerate the baseline")
    group.add_argument(
        "--check", action="store_true", help="compare the tree with the baseline"
    )
    args = parser.parse_args(argv)

    if args.write:
        return write()
    if args.check:
        return check()
    return report()


if __name__ == "__main__":
    raise SystemExit(main())
