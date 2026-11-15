#!/usr/bin/env python3
"""Check that every `mise run <task>` the repository tells a reader to type names a real task.

The docs and the scripts' own messages name tasks (`mise run audit:verify`, `mise run hk:check`).
A name that is neither a task nor a task alias is a command that fails for whoever follows it.
The task list comes from `mise tasks --json`, so it includes the user's global tasks; the
vendored upstream copies are not scanned.

`--self-test` first proves the check fails on a name that does not exist.

Exit status is 0 when every name resolves and 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def task_names() -> set[str]:
    out = subprocess.run(
        ["mise", "tasks", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    names: set[str] = set()
    for task in json.loads(out):
        names.add(task["name"])
        names.update(task.get("aliases") or [])
    return names


def scanned_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md", "scripts/*.py", "mise/**/*.toml", ".mise.toml"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [
        REPO_ROOT / line
        for line in out.splitlines()
        if "/upstream/" not in line and not line.endswith("check_doc_commands.py")
    ]


# A `mise run` command up to the end of its code span, quote or line.
COMMAND = re.compile(r"mise run((?:[ \t]+[^ \t`'\"]+)+)")
# Prose punctuation and Markdown emphasis that can follow a command, not part of a task name.
TRAILING = ".,;)*"


def expand(token: str) -> list[str]:
    """`audit:verify/measure/acceptance` is shorthand for three tasks in one namespace.

    Each part is checked: `hk:check/nonexistent` yields `hk:check` and `hk:nonexistent`.
    A monorepo path (`//dir:task`) is one name, and a placeholder (`<task>`) names none.
    """
    if token.startswith(("<", "//")) or "/" not in token:
        return [] if token.startswith("<") else [token]
    first, *rest = token.split("/")
    namespace = first.rpartition(":")[0]
    return [first] + [f"{namespace}:{part}" if namespace else part for part in rest]


def task_tokens(arguments: str) -> list[str]:
    """The task names in one `mise run` argument string.

    A `:::` starts another task. Options (`-x`, `--force`) before a task are skipped; after the
    task, everything up to the next `:::` is the task's own arguments.
    """
    tasks: list[str] = []
    expecting = True
    for token in arguments.split():
        if token == ":::":
            expecting = True
            continue
        if not expecting:
            continue
        if token.startswith("-"):
            continue
        tasks.extend(expand(token.rstrip(TRAILING)))
        expecting = False
    return tasks


def unknown(texts: dict[str, str], names: set[str]) -> list[str]:
    found = []
    for where, text in texts.items():
        for number, line in enumerate(text.split("\n"), 1):
            for match in COMMAND.finditer(line):
                for task in task_tokens(match.group(1)):
                    if task not in names:
                        found.append(
                            f"{where}:{number}: `mise run {task}` is not a task"
                        )
    return found


SELF_TEST_BAD = [
    "mise run no-such-task-xyz",
    "mise run {ok} ::: no-such-task-xyz",
    "mise run --force no-such-task-xyz",
    "mise run audit:verify/nonexistent",
    "mise run hk:check/nonexistent",
]
SELF_TEST_GOOD = [
    "`mise run {ok}`",
    "mise run {ok} -- --prefix MOD",
    "mise run {ok} ::: {ok}",
    "Then mise run {ok}.",
    "(mise run audit:verify/measure/acceptance).**",
    "`mise run <task>`",
]


def self_test(names: set[str]) -> None:
    """Every bad form must be reported and every good form accepted."""
    ok = "verify" if "verify" in names else min(names)
    for sample in SELF_TEST_BAD:
        if not unknown({"probe": sample.format(ok=ok)}, names):
            raise SystemExit(f"self-test: not reported: {sample.format(ok=ok)!r}")
    for sample in SELF_TEST_GOOD:
        if unknown({"probe": sample.format(ok=ok)}, names):
            raise SystemExit(f"self-test: wrongly reported: {sample.format(ok=ok)!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--self-test", action="store_true", help="prove the check can fail first"
    )
    args = parser.parse_args()

    names = task_names()
    if args.self_test:
        self_test(names)

    texts = {
        str(path.relative_to(REPO_ROOT)): path.read_text(encoding="utf-8")
        for path in scanned_files()
    }
    found = unknown(texts, names)
    for line in found:
        print(f"problem: {line}")
    if found:
        return 1
    print(f"every `mise run` name resolves: {len(texts)} files scanned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
