#!/usr/bin/env python3
"""A mutation test for the checker.

`verify_audit.py` is only worth trusting if it **fails when it should**. This script breaks one
thing at a time in the working tree - a count, a heading, a table, a fence, a link, a private
path, the registry, a vendored file - and asserts that the right check fires and that the tree is
restored afterwards.

It mutates the tree in place, because the privacy scan derives its identity tokens from this
repository's own git history and from the machine name, and a copy of the tree in a temporary
directory would have neither.

Stdlib only. No compiler, no CMake, no network.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFIER = REPO_ROOT / "scripts" / "verify_audit.py"

# The verifier is fast - about a second - but it reads the build artifacts, and a hang should
# fail the mutation that caused it rather than stall the whole suite.
VERIFIER_TIMEOUT = 60

PARKED = REPO_ROOT / "PARKED.md"
DECISIONS = REPO_ROOT / "docs" / "cxx26-features-audit" / "decisions.md"
OPEN_ITEMS = REPO_ROOT / "docs" / "cxx26-features-audit" / "open-items.md"
AUDIT_README = REPO_ROOT / "docs" / "cxx26-features-audit" / "README.md"
VENDORED = REPO_ROOT / "docs" / "cxx26-features-audit" / "upstream" / "fmt" / "base.h"
MEASUREMENTS = REPO_ROOT / "docs" / "cxx26-features-audit" / "measurements.json"
ACCEPTANCE = REPO_ROOT / "docs" / "cxx26-features-audit" / "acceptance.json"
CITATIONS = REPO_ROOT / "docs" / "cxx26-features-audit" / "citations.json"
PROBE = REPO_ROOT / "scripts" / "_privacy_probe.tmp"


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"the mutation target is not in {path.name}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def insert_after(path: Path, anchor: str, text: str) -> None:
    lines = path.read_text(encoding="utf-8").split("\n")
    for number, line in enumerate(lines):
        if anchor in line:
            lines.insert(number + 1, text)
            path.write_text("\n".join(lines), encoding="utf-8")
            return
    raise SystemExit(f"the mutation anchor is not in {path.name}: {anchor!r}")


def mutate_counts() -> None:
    replace(PARKED, "**81 open items**", "**82 open items**")


def mutate_dangling_id() -> None:
    append(PARKED, "\nSee FMT-99 for the thing that does not exist.\n")


def mutate_decisions() -> None:
    text = DECISIONS.read_text(encoding="utf-8")
    for line in text.split("\n"):
        if line.startswith("### ENV-3"):
            DECISIONS.write_text(text.replace(line + "\n", "", 1), encoding="utf-8")
            return
    raise SystemExit("no ENV-3 heading in decisions.md")


def mutate_split_table() -> None:
    insert_after(OPEN_ITEMS, "| FMT-8 |", "\na paragraph in the middle of a table\n")


def mutate_fence() -> None:
    append(AUDIT_README, "\n```\n")


def mutate_link() -> None:
    replace(
        AUDIT_README,
        "[open-items.md](open-items.md)",
        "[open-items.md](open-items-missing.md)",
    )


def mutate_privacy() -> None:
    # The probe is assembled from parts so that this file does not itself contain a home path -
    # the privacy scan reads the working tree, this file included.
    home = "/" + "Users" + "/someone/file.txt"
    PROBE.write_text(f"a home path: {home}\n", encoding="utf-8")


def mutate_registry() -> None:
    replace(
        OPEN_ITEMS,
        "| FMT-1 | Does `FMT_STATIC_FORMAT` compile",
        "| FMT-1 | Does `FMT_STATIC_FORMAT` really compile",
    )


def mutate_parts() -> None:
    text = AUDIT_README.read_text(encoding="utf-8")
    for line in text.split("\n"):
        if line.startswith("| 17 |"):
            AUDIT_README.write_text(text.replace(line + "\n", "", 1), encoding="utf-8")
            return
    raise SystemExit("no part 17 row in the audit README")


def mutate_upstream() -> None:
    with VENDORED.open("a", encoding="utf-8") as handle:
        handle.write("\n// a byte that is not upstream's\n")


def mutate_contradiction() -> None:
    insert_after(
        OPEN_ITEMS,
        "| FMT-8 |",
        "| FMT-9 | Does the vcpkg `quill` port have an external-fmt feature? | a compile |",
    )


def mutate_measurements() -> None:
    # The baseline is a derived artifact. A number in it that no longer matches the tree is
    # exactly what the staleness check exists to catch.
    replace(
        MEASUREMENTS,
        '"code_lines": 967,',
        '"code_lines": 968,',
    )


def mutate_acceptance() -> None:
    # The bar is a standard, and a standard can be tightened. Pretending it demands zero
    # untested exported functions must fail against a tree that has four.
    replace(
        ACCEPTANCE,
        '"metric": "api.exported_functions_untested",\n'
        '      "kind": "ceiling",\n'
        '      "threshold": 4,',
        '"metric": "api.exported_functions_untested",\n'
        '      "kind": "ceiling",\n'
        '      "threshold": 0,',
    )


def mutate_citation_anchor() -> None:
    # The citation anchor is a derived artifact: a hash of what every cited line says. A
    # hash that no longer matches the source it describes is exactly what the check exists
    # to catch - and this is the same comparison a line of source moving under a citation
    # makes, with the source left alone.
    text = CITATIONS.read_text(encoding="utf-8")
    for line in text.split("\n"):
        if '"sha256:' in line:
            CITATIONS.write_text(text.replace(line, line.replace("sha256:", "sha256:0"), 1), "utf-8")
            return
    raise SystemExit("no hash in citations.json")


MUTATIONS = [
    ("the counts the prose claims are the counts the registry holds", mutate_counts),
    ("every referenced item ID resolves", mutate_dangling_id),
    ("the decisions sheet matches the owner-decision items", mutate_decisions),
    ("Markdown tables have a uniform shape", mutate_split_table),
    ("code fences are balanced", mutate_fence),
    ("relative links resolve", mutate_link),
    ("no private name, path or host is in a tracked file", mutate_privacy),
    ("the committed registry is up to date", mutate_registry),
    ("the committed measurement baseline is up to date", mutate_measurements),
    ("the acceptance bar holds", mutate_acceptance),
    ("the audit's citations still point at the code they name", mutate_citation_anchor),
    ("the parts tables agree", mutate_parts),
    ("the vendored upstream copies match the manifest", mutate_upstream),
    ("an item is not open and answered at the same time", mutate_contradiction),
]


def run_verifier() -> tuple[int, str]:
    # A bounded run. If the verifier hangs, the mutation fails loudly instead of the suite
    # hanging with it - and the tree is still restored, because the timeout unwinds here.
    try:
        result = subprocess.run(
            [sys.executable, str(VERIFIER)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=VERIFIER_TIMEOUT,
        )
    except subprocess.TimeoutExpired as expired:
        output = (expired.stdout or "") + (expired.stderr or "")
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return 1, f"the verifier did not finish within {VERIFIER_TIMEOUT}s\n{output}"
    return result.returncode, result.stdout + result.stderr


def git_status() -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


# The only files a mutation may touch. The restore writes these back byte for byte - it does NOT
# use `git checkout`, which would revert every uncommitted change in the tree, including the
# work being tested.
MUTABLE = [PARKED, DECISIONS, OPEN_ITEMS, AUDIT_README, VENDORED, MEASUREMENTS, ACCEPTANCE,
           CITATIONS]


def snapshot() -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.exists() else None for path in MUTABLE}


def write_atomically(path: Path, content: bytes) -> None:
    """Write a file so that an interruption can never leave it truncated.

    `path.write_bytes` opens with "wb", which truncates first and writes second. A signal
    arriving between the two leaves a zero-byte file - and that is exactly what happened here:
    the test was interrupted mid-restore and left `PARKED.md` empty. The file is written to a
    sibling temporary path and then moved into place with `os.replace`, which is atomic on
    POSIX: the target is either the old file or the new one, never a half-written one.
    """
    temporary = path.with_name(path.name + ".restore-tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def restore(saved: dict[Path, bytes | None]) -> None:
    for path, content in saved.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            write_atomically(path, content)
    PROBE.unlink(missing_ok=True)


class Interrupted(BaseException):
    """Raised from the signal handler, so that the restore still runs."""


def install_signal_handlers() -> None:
    """Make SIGTERM and SIGINT unwind through the `finally`, so the tree is restored.

    By default a SIGTERM terminates the process immediately: no `finally`, no restore, and the
    mutation stays in the tree. That is how a tracked file was left empty once already.
    """

    def handler(signum, frame):  # noqa: ARG001 - the signal handler's signature is fixed
        raise Interrupted(f"interrupted by signal {signum}")

    for signal_number in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(signal_number, handler)
        except (ValueError, OSError):
            # Not the main thread, or the platform does not allow it. The atomic write still
            # protects the tree; only the promptness of the restore is lost.
            pass


def main() -> int:
    install_signal_handlers()
    print(f"{len(MUTATIONS)} mutations, each of which must make the verifier fail\n")

    passed = 0
    failures = []
    interrupted = None
    for expected, mutate in MUTATIONS:
        before = git_status()
        saved = snapshot()
        try:
            mutate()
            code, output = run_verifier()
            # The verifier prints "  FAIL  <name>" for a failing check and "  ok    <name>" for a
            # passing one, so the name alone is not enough to tell which happened.
            fired = f"FAIL  {expected}" in output
            if code != 0 and fired:
                print(f"  ok    {expected}")
                passed += 1
            else:
                print(f"  FAIL  {expected}")
                if code == 0:
                    failures.append(f"{expected}: the verifier exited 0")
                else:
                    failures.append(f"{expected}: the verifier failed, but not on this check")
        except Interrupted as error:
            # The tree is restored by the `finally` below; then the run stops, because the
            # interruption is not a failure of the checker.
            interrupted = error
            print(f"  interrupted during: {expected}")
        finally:
            restore(saved)
        if git_status() != before:
            failures.append(f"{expected}: the tree was not restored")
        if interrupted is not None:
            break

    print()
    if interrupted is not None:
        print(f"  {interrupted}")
        print("  the tree was restored before the run stopped")
        return 130
    if failures:
        for failure in failures:
            print(f"  {failure}")
        print(f"\n{passed}/{len(MUTATIONS)} mutations detected")
        return 1
    print(f"{passed}/{len(MUTATIONS)} mutations detected, and the tree was restored every time")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
