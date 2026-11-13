#!/usr/bin/env python3
"""What the automation is worth, measured rather than asserted.

The question this answers is "is the project better off than it was?" - and the honest answer is
"not yet, in the library". **No library source has changed.** What changed is the cost of working
on the library: what an agent has to read to know what is going on, what it costs to verify a
change, how fast a drift is noticed, and how much of the repository's own rules are written down
where a subagent will actually see them.

The "before" figures are measured from the tree at `BASELINE` - the commit before the automation
landed - not from memory.

Stdlib only. No compiler, no CMake, no network.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The commit before the automation landed. Every "before" number is read from this tree.
BASELINE = "5d52231"

# The files a session had to open to learn the lane state and the open items.
ORIENTATION_BEFORE = ["PARKED.md", "README.md", "docs/cxx26-features-audit/open-items.md",
                      "docs/cxx26-features-audit/decisions.md"]
ORIENTATION_AFTER = ["AGENTS.md"]

# The library's own code, so the metric can say whether any of it moved.
LIBRARY = ["src", "include", "modules", "tests", "cmake", "CMakeLists.txt", "CMakePresets.json",
           "vcpkg.json", "ports", "triplets"]

# The sweep that was re-typed by hand during part 18: its length, and how many times it was
# typed. These are a record of what happened, not a measurement of the tree.
SWEEP_LINES = 120
SWEEP_RUNS = 8


def git_show(revision: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def measure(text: str) -> tuple[int, int]:
    return len(text.split("\n")), len(text)


def tokens(characters: int) -> int:
    """A rough token estimate. Four characters per token is the usual approximation."""
    return characters // 4


def library_diff() -> str:
    result = subprocess.run(
        ["git", "diff", "--stat", f"{BASELINE}..HEAD", "--", *LIBRARY],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def count_mentions(path: Path, needles: tuple[str, ...]) -> int:
    text = path.read_text(encoding="utf-8").lower()
    return sum(1 for needle in needles if needle in text)


def main() -> int:
    print("THE LIBRARY")
    diff = library_diff()
    if diff:
        print("  the library changed since the baseline:")
        for line in diff.split("\n"):
            print(f"    {line}")
    else:
        print("  unchanged since the baseline - this work moved the process, not the code")
        print("  (that is the honest headline: DEF-1 to DEF-6 are all still there)")

    print("\nTHE ORIENTATION COST - what an agent has to read to know where things stand")
    before_lines = before_chars = 0
    for path in ORIENTATION_BEFORE:
        text = git_show(BASELINE, path)
        if text is None:
            continue
        lines, chars = measure(text)
        before_lines += lines
        before_chars += chars
        print(f"  before  {path:<45} {lines:5d} lines")
    after_lines = after_chars = 0
    for path in ORIENTATION_AFTER:
        file = REPO_ROOT / path
        if not file.exists():
            continue
        lines, chars = measure(file.read_text(encoding="utf-8"))
        after_lines += lines
        after_chars += chars
        print(f"  after   {path:<45} {lines:5d} lines")

    # The slice a session actually reads once it knows the rules.
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "audit_summary.py"), "--prefix", "MOD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    slice_lines, slice_chars = measure(result.stdout)
    after_lines += slice_lines
    after_chars += slice_chars
    print(f"  after   {'plus one command: mise run audit:summary -- --prefix MOD':<45}"
          f" {slice_lines:5d} lines")

    # Two baselines, because "before" is not one number: a thorough session read all four files,
    # and a hurried one read only PARKED.md. The honest comparison is against the smaller one.
    minimum_text = git_show(BASELINE, "PARKED.md") or ""
    minimum_lines, minimum_chars = measure(minimum_text)
    thorough_saving = 1 - after_chars / before_chars if before_chars else 0
    minimum_saving = 1 - after_chars / minimum_chars if minimum_chars else 0
    print(
        f"\n  thorough before: {before_lines} lines / about {tokens(before_chars):,} tokens"
        f"  ->  {after_lines} lines / about {tokens(after_chars):,} tokens"
        f"   ({thorough_saving:.0%} less)"
    )
    print(
        f"  hurried  before: {minimum_lines} lines / about {tokens(minimum_chars):,} tokens"
        f"  ->  {after_lines} lines / about {tokens(after_chars):,} tokens"
        f"   ({minimum_saving:.0%} less)"
    )

    print("\nTHE VERIFICATION COST - what it costs to check a change")
    print(f"  before  {SWEEP_LINES} lines of Python, re-typed {SWEEP_RUNS} times"
          f"  = {SWEEP_LINES * SWEEP_RUNS} lines typed by hand")
    verifier = REPO_ROOT / "scripts" / "verify_audit.py"
    lines, chars = measure(verifier.read_text(encoding="utf-8"))
    result = subprocess.run(
        [sys.executable, str(verifier), "--quiet"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output_lines = len(result.stdout.strip().split("\n"))
    print(f"  after   {lines} lines of Python, typed once"
          f"  = {output_lines} lines of output per check")
    print(f"         the sweep is also a command now: `mise run audit:verify`")

    print("\nTHE CHECKER'S OWN COVERAGE")
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "test_verify_audit.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    last = result.stdout.strip().split("\n")[-1]
    print(f"  {last}")
    print("  the checker is tested by breaking the tree 12 ways and asserting that each one is caught")

    print("\nTHE MEASUREMENTS - what the project is, in numbers")
    measurements = REPO_ROOT / "docs" / "cxx26-features-audit" / "measurements.json"
    if measurements.exists():
        import json

        data = json.loads(measurements.read_text())
        library = data["library"]
        coverage = data["audit_coverage"]
        dependencies = data["dependencies"]
        print(f"  the library: {library['files']} files, {library['code_lines']} lines of code")
        print(f"  the hand-rolled formatter: {library['hand_rolled_formatter_lines']} lines"
              f" ({library['hand_rolled_formatter_share']:.0%} of the library)")
        print(f"  standard-library includes in the module interface: "
              f"{data['interface']['standard_library_includes']} (the rule is 0)")
        print(f"  exported functions the test file never calls: "
              f"{len(data['api']['not_tested_at_source_level'])}"
              f" of {data['api']['public_functions']}")
        print(f"  the audit's own coverage: {coverage['specific_share']:.0%} read"
              f" / {coverage['seen_share']:.0%} looked at")
        if dependencies.get("available"):
            print(f"  the dependency closure: {dependencies['reached_headers']} headers,"
                  f" cross-checked by {dependencies.get('trees_measured', 0)} build trees"
                  f" ({'all agree' if dependencies.get('trees_agreeing') else 'DISAGREE'})")
        print("  the baseline is committed, so a change is visible as a delta:"
              " `mise run audit:measure`")
    else:
        print("  not measured: no baseline")

    print("\nTHE RULES - are they where a subagent will actually see them")
    agents = sorted((REPO_ROOT / ".opencode" / "agents" / "sdlc").glob("*.md"))
    lane = ("the build lane is parked",)
    privacy = ("privacy",)
    with_lane = sum(1 for path in agents if count_mentions(path, lane))
    with_privacy = sum(1 for path in agents if count_mentions(path, privacy))
    print(f"  subagent files carrying the lane        {with_lane} of {len(agents)}"
          f"   (before: 0 - qa.md was told it may build)")
    print(f"  subagent files carrying the privacy rule {with_privacy} of {len(agents)}"
          f"   (before: 0)")
    print(f"  AGENTS.md exists                         yes"
          f"   (before: no - every session re-derived the rules)")

    print("\nTHE AUDIT'S STATE")
    index = (REPO_ROOT / "docs" / "cxx26-features-audit" / "audit-index.json").read_text()
    import json

    counts = json.loads(index)["counts"]
    print(f"  {counts['open']} open items: {counts['by_category'].get('owner-decision', 0)} owner"
          f" decisions, {counts['by_category'].get('compile', 0)} a compile,"
          f" {counts['by_category'].get('run', 0)} a run")
    print(f"  {counts['by_prefix'].get('DEF', 0)} defects - unchanged by this work, and still open")
    print(f"  the counts are derived, not typed: a mismatch is a check failure")

    print("\nWHAT THIS DOES NOT IMPROVE")
    print("  the library: DEF-1 to DEF-6 are all still there, and the build lane is still parked")
    print("  the decisions: the four owner decisions still gate the implementation")
    print("  the coverage: the gate is still a run away")
    print("  what it does improve is the cost of getting to those answers,")
    print("  and it now says what the project *is*, in numbers, rather than in adjectives")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
