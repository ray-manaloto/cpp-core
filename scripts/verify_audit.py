#!/usr/bin/env python3
"""Every check that does not need a compiler.

This is the command that replaces the ad-hoc verification sweeps: item counts, duplicate IDs,
dangling references, the decisions sheet against the open list, the counts the prose claims,
Markdown table shape, fence balance, relative links, the parts tables, the privacy scan, and the
vendored upstream copies.

It does **not** build, configure, compile, link or run anything. The build lane is parked; a
check that needs a compiler is written down as an open item instead.

Stdlib only. Exit status is 0 when everything passes and 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_index  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "docs" / "cxx26-features-audit"

OPEN_ITEMS = AUDIT_DIR / "open-items.md"
DECISIONS = AUDIT_DIR / "decisions.md"
AUDIT_README = AUDIT_DIR / "README.md"
INDEX_PATH = AUDIT_DIR / "audit-index.json"
MEASUREMENTS_PATH = AUDIT_DIR / "measurements.json"
ACCEPTANCE_PATH = AUDIT_DIR / "acceptance.json"
CITATIONS_PATH = AUDIT_DIR / "citations.json"
UPSTREAM_MANIFEST = AUDIT_DIR / "upstream" / "manifest.json"
PARKED = REPO_ROOT / "PARKED.md"
ROOT_README = REPO_ROOT / "README.md"
MEASURE = REPO_ROOT / "scripts"

# The documents whose prose and tables are checked.
AUDIT_DOCS = sorted(AUDIT_DIR.glob("*.md"))
MARKDOWN_DOCS = AUDIT_DOCS + [PARKED, ROOT_README]

# Files that are not ours: the vendored upstream copies. They are scanned for identity tokens
# but not for structural patterns, because a third-party source may legitimately contain a path.
VENDORED_PREFIX = "docs/cxx26-features-audit/upstream/"

# The count the audit had when parts 17 and 18 were written. History, not a claim about now.
HISTORICAL_TOTALS = {83, 84}

# A private name is never written into a tracked file. The patterns are *derived* at run time -
# from this machine's git identity, from this repository's own history, and from the machine name
# - so that no private value is stored in the repository. An untracked file can add more.
PRIVACY_PATTERNS_FILE = REPO_ROOT / ".audit" / "privacy-patterns.txt"
STRUCTURAL_PATTERNS = [
    # The patterns are written so that they do not match their own source, and so that a URL
    # path segment is not mistaken for a home directory: the lookbehind requires that the
    # leading slash does not follow a word character.
    (r"(?<![A-Za-z0-9._-])/[Uu]sers/[A-Za-z0-9._-]+/", "a macOS home path"),
    (r"(?<![A-Za-z0-9._-])/home/[A-Za-z0-9._-]+/", "a Linux home path"),
    (r"\b[a-z0-9][a-z0-9.-]*\.ts\.net\b", "a tailnet host name"),
]

CHECKS: list[tuple[str, object]] = []


def check(name):
    def decorate(function):
        CHECKS.append((name, function))
        return function

    return decorate


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def relative(path: Path) -> str:
    """The path as the repository refers to it."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def word_to_number(word: str) -> int | None:
    words = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
    }
    return words.get(word.strip().lower())


# --------------------------------------------------------------------------------------- checks


@check("the committed registry is up to date")
def check_registry_fresh() -> list[str]:
    if not INDEX_PATH.exists():
        return [f"missing {relative(INDEX_PATH)} - run `mise run audit:index`"]
    expected = audit_index.render(audit_index.build_index())
    if read(INDEX_PATH) != expected:
        return [
            f"{relative(INDEX_PATH)} is stale - run `mise run audit:index` "
            f"and commit the result"
        ]
    return []


@check("the committed measurement baseline is up to date")
def check_measurements_fresh() -> list[str]:
    if not MEASUREMENTS_PATH.exists():
        return [f"missing {relative(MEASUREMENTS_PATH)} - run `mise run audit:measure --write`"]
    result = subprocess.run(
        [sys.executable, str(MEASURE / "measure.py"), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    return [
        f"{relative(MEASUREMENTS_PATH)} is stale - run `mise run audit:measure --write` "
        f"and commit the result"
    ]


@check("the audit's citations still point at the code they name")
def check_citations_anchored() -> list[str]:
    if not CITATIONS_PATH.exists():
        return [f"missing {relative(CITATIONS_PATH)} - run `mise run audit:anchor`"]
    result = subprocess.run(
        [sys.executable, str(MEASURE / "anchor_citations.py"), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    problems = []
    for line in (result.stdout + result.stderr).split("\n"):
        stripped = line.strip()
        if stripped.startswith("problem:"):
            problems.append(stripped[len("problem:"):].strip())
    if not problems:
        problems.append(
            "the citations have drifted - re-anchor them and run `mise run audit:anchor`"
        )
    return problems


@check("the acceptance bar holds")
def check_acceptance_bar() -> list[str]:
    if not ACCEPTANCE_PATH.exists():
        return [f"missing {relative(ACCEPTANCE_PATH)} - the bar is a standard; write it down"]
    result = subprocess.run(
        [sys.executable, str(MEASURE / "measure.py"), "--acceptance"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    problems = []
    for line in (result.stdout + result.stderr).split("\n"):
        stripped = line.strip()
        if stripped.startswith("violation:"):
            problems.append(stripped[len("violation:"):].strip())
    if not problems:
        problems.append(
            "the acceptance bar is violated - run `mise run audit:measure -- --acceptance`"
        )
    return problems


@check("no duplicate item IDs")
def check_duplicate_ids() -> list[str]:
    problems = []
    index = audit_index.build_index()
    seen: dict[str, int] = {}
    for item in index["items"] + index["answered_items"]:
        seen[item["id"]] = seen.get(item["id"], 0) + 1
    for item_id, count in sorted(seen.items()):
        if count > 1:
            problems.append(f"{item_id} appears {count} times in the registry")
    return problems


@check("every referenced item ID resolves")
def check_dangling_ids() -> list[str]:
    index = audit_index.build_index()
    known = {item["id"] for item in index["items"] + index["answered_items"]}
    # An ID that is only ever mentioned in prose about another document's history is still known
    # if the registry knows it; the check below is about IDs that resolve to nothing at all.
    pattern = re.compile(r"\b((?:DEF|FMT|QUIL|TOOL|MOD|REFL|MAC|COV|BUILD|VCPKG|ENV)-\d+)\b")
    problems = []
    for path in MARKDOWN_DOCS:
        for number, line in enumerate(read(path).split("\n"), 1):
            for match in pattern.finditer(line):
                if match.group(1) not in known:
                    problems.append(
                        f"{relative(path)}:{number} references {match.group(1)}, "
                        f"which is not in the registry"
                    )
    return problems


@check("an item is not open and answered at the same time")
def check_no_contradiction() -> list[str]:
    index = audit_index.build_index()
    open_ids = {item["id"] for item in index["items"] if item["state"] == "open"}
    answered_ids = {item["id"] for item in index["answered_items"]}
    both = sorted(open_ids & answered_ids)
    return [f"{item_id} is listed as both open and answered" for item_id in both]


@check("the decisions sheet matches the owner-decision items")
def check_decisions() -> list[str]:
    index = audit_index.build_index()
    # Owner decisions can be in open items OR answered items (once answered, they move to section 13)
    owner_open = sorted(
        item["id"] for item in index["items"] if item["category"] == "owner-decision"
    )
    owner_answered = sorted(
        item["id"] for item in index["answered_items"] if item["category"] == "owner-decision"
    )
    owner = sorted(set(owner_open) | set(owner_answered))
    headings = sorted(re.findall(r"^### ([A-Z]+-\d+)\b", read(DECISIONS), re.M))
    problems = []
    for item_id in sorted(set(owner) ^ set(headings)):
        where = "the open/answered list only" if item_id in owner else "the decisions sheet only"
        problems.append(f"{item_id} is in {where}")
    if len(owner) != len(headings):
        problems.append(f"{len(owner)} owner decisions but {len(headings)} headings")
    return problems


@check("the counts the prose claims are the counts the registry holds")
def check_counts() -> list[str]:
    index = audit_index.build_index()
    counts = index["counts"]
    by_prefix = counts["by_prefix"]
    total = counts["open"]
    owner = counts["by_category"].get("owner-decision", 0)
    measurement = total - owner

    breakdown = (
        f"{by_prefix.get('DEF', 0)} defects, "
        f"{by_prefix.get('FMT', 0)} fmt/`constexpr` questions, "
        f"{by_prefix.get('QUIL', 0)} quill questions, "
        f"{by_prefix.get('TOOL', 0)} tooling questions, "
        f"{by_prefix.get('MOD', 0)} `import std;` questions, "
        f"{by_prefix.get('REFL', 0)} reflection questions, "
        f"{by_prefix.get('MAC', 0)} macro questions, "
        f"{by_prefix.get('COV', 0)} coverage to-dos, "
        f"{by_prefix.get('BUILD', 0)} build questions "
        f"and {by_prefix.get('ENV', 0)} environment questions - **{total} in all**"
    )
    summary = (
        f"**{total} open items**: {owner} owner decisions, 0 registry reads, "
        f"{measurement} settled by a compile, a run or a preprocessor pass"
    )

    problems = []
    parked = read(PARKED)
    # The prose is wrapped, so the comparison is made against a whitespace-normalised copy.
    parked_flat = " ".join(parked.split())
    breakdown_flat = " ".join(breakdown.split())
    summary_flat = " ".join(summary.split())
    if breakdown_flat not in parked_flat:
        problems.append(
            "PARKED.md's breakdown does not match the registry. It should say:\n"
            f"    {breakdown}"
        )
    if summary_flat not in parked_flat:
        problems.append(
            "PARKED.md's summary does not match the registry. It should say:\n"
            f"    {summary}"
        )

    for number in sorted(set(re.findall(r"\*\*(\d+) open items\*\*", parked_flat))):
        value = int(number)
        if value != total and value not in HISTORICAL_TOTALS:
            problems.append(
                f"PARKED.md claims {value} open items; the registry says {total}. "
                f"History is written as 'had N open items', not '**N open items**'."
            )

    defects = counts["by_prefix"].get("DEF", 0)
    readme = read(AUDIT_README)
    for match in re.finditer(r"There are (\w+) now", readme):
        value = word_to_number(match.group(1))
        if value is not None and value != defects:
            problems.append(
                f"the audit README says 'There are {match.group(1)} now' but the registry "
                f"holds {defects} defects"
            )
    return problems


@check("the parts tables agree")
def check_parts() -> list[str]:
    index = audit_index.build_index()
    from_index = [part["part"] for part in index["parts"]]
    from_parked = _parked_parts()
    problems = []
    if from_index != from_parked:
        problems.append(
            f"the audit README lists parts {from_index} and PARKED.md lists {from_parked}"
        )
    return problems


def _parked_parts() -> list[int]:
    """The part numbers in PARKED.md's parts table."""
    parts: list[int] = []
    in_section = False
    for line in read(PARKED).split("\n"):
        if line.startswith("## "):
            in_section = "research lane" in line.lower()
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].isdigit():
            parts.append(int(cells[0]))
    return parts


@check("Markdown tables have a uniform shape")
def check_tables() -> list[str]:
    problems = []
    for path in MARKDOWN_DOCS:
        table: list[tuple[int, int]] = []
        in_fence = False
        for number, line in enumerate(read(path).split("\n"), 1):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if line.startswith("|"):
                table.append((number, line.count("|")))
                continue
            problems.extend(_table_problems(path, table))
            table = []
        problems.extend(_table_problems(path, table))
    return problems


def _table_problems(path: Path, table: list[tuple[int, int]]) -> list[str]:
    if len(table) < 2:
        return []
    problems = []
    counts = {count for _, count in table}
    if len(counts) > 1:
        problems.append(
            f"{relative(path)}:{table[0][0]} - a table has rows with "
            f"{sorted(counts)} pipes"
        )
    # A table that does not start with a header separator is a table that a paragraph split in
    # two - which renders as a table and then as plain text.
    separator = re.compile(r"^\|[\s:-]*\|[\s:|-]*$")
    lines = read(path).split("\n")
    second = lines[table[1][0] - 1] if table[1][0] <= len(lines) else ""
    if not separator.match(second.strip()):
        problems.append(
            f"{relative(path)}:{table[0][0]} - a table does not start with a "
            f"header separator (line {table[1][0]}: {second.strip()[:40]!r}). A table split by "
            f"a paragraph renders as a table and then as plain text."
        )
    return problems


@check("code fences are balanced")
def check_fences() -> list[str]:
    problems = []
    for path in MARKDOWN_DOCS:
        count = read(path).count("```")
        if count % 2:
            problems.append(f"{relative(path)} has {count} fence markers")
    return problems


@check("relative links resolve")
def check_links() -> list[str]:
    problems = []
    pattern = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
    for path in MARKDOWN_DOCS:
        base = path.parent
        for match in pattern.finditer(read(path)):
            target = match.group(2)
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target_path = target.split("#")[0]
            if not target_path:
                continue
            if not (base / target_path).exists():
                problems.append(
                    f"{relative(path)} links to {target}, which does not exist"
                )
    return problems


@check("no private name, path or host is in a tracked file")
def check_privacy() -> list[str]:
    tokens = _privacy_tokens()
    files = _tracked_files()
    problems = []
    scanned = 0
    skipped = 0
    for path in files:
        relative = str(path.relative_to(REPO_ROOT))
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        vendored = relative.startswith(VENDORED_PREFIX)
        for token in tokens:
            if token in text:
                problems.append(f"{relative} contains a private value")
                break
        if vendored:
            skipped += 1
            continue
        for pattern, description in STRUCTURAL_PATTERNS:
            if re.search(pattern, text):
                problems.append(f"{relative} contains {description}")
    if not tokens:
        problems.append(
            "no identity tokens could be derived - the privacy scan ran but could not "
            "check for this machine's identity"
        )
    print(
        f"    privacy: {scanned} files scanned "
        f"({skipped} vendored upstream copies), {len(tokens)} identity tokens, "
        f"{len(STRUCTURAL_PATTERNS)} structural patterns"
    )
    return problems


def _tracked_files() -> list[Path]:
    names = git("ls-files", "-z").split("\0")
    extra = git("ls-files", "-z", "--others", "--exclude-standard").split("\0")
    paths = []
    for name in names + extra:
        if not name or name.startswith("build/"):
            continue
        paths.append(REPO_ROOT / name)
    return paths


def _privacy_tokens() -> list[str]:
    """The private values, derived at run time so that none is stored in the repository."""
    raw: set[str] = set()

    for key in ("user.name", "user.email"):
        value = git("config", "--get", key)
        if value:
            raw.add(value)
            raw.add(value.split("@")[0])

    authors = git("log", "--format=%an%n%ae")
    for line in authors.split("\n"):
        line = line.strip()
        if line:
            raw.add(line)
            raw.add(line.split("@")[0])

    host = socket.gethostname().strip()
    if host and len(host) >= 5 and host.lower() != "localhost":
        raw.add(host)

    if PRIVACY_PATTERNS_FILE.exists():
        for line in read(PRIVACY_PATTERNS_FILE).split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                raw.add(line)

    common = {
        "root",
        "admin",
        "user",
        "guest",
        "build",
        "release",
        "unknown",
        "example",
        "localhost",
        "github",
        "actions",
        "runner",
    }
    tokens = []
    for value in raw:
        value = value.strip()
        if len(value) < 4 or value.lower() in common:
            continue
        if value in tokens:
            continue
        tokens.append(value)
    return tokens


@check("the vendored upstream copies match the manifest")
def check_upstream() -> list[str]:
    if not UPSTREAM_MANIFEST.exists():
        return [f"missing {relative(UPSTREAM_MANIFEST)}"]
    manifest = json.loads(read(UPSTREAM_MANIFEST))
    problems = []
    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        if not path.exists():
            problems.append(f"{entry['path']} is missing")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            problems.append(
                f"{entry['path']} has sha256 {digest[:16]}..., "
                f"the manifest says {entry['sha256'][:16]}..."
            )
    return problems


# ----------------------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print only the failures",
    )
    args = parser.parse_args(argv)

    index = audit_index.build_index()
    counts = index["counts"]
    print(
        f"the audit: {counts['open']} open, {counts['answered']} answered, "
        f"{counts['contingent']} contingent, {len(index['parts'])} parts"
    )

    failures = 0
    for name, function in CHECKS:
        # A check that raises is a failure, not a reason to stop: the rest of the sweep still has
        # something to say.
        try:
            problems = function()
        except Exception as error:  # noqa: BLE001 - the point is to report, not to crash
            problems = [f"the check raised {type(error).__name__}: {error}"]
        if problems:
            failures += 1
            print(f"  FAIL  {name}")
            for problem in problems:
                print(f"        {problem}")
        elif not args.quiet:
            print(f"  ok    {name}")

    if failures:
        print(f"\n{failures} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
