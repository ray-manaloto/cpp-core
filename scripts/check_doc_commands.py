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
COMMAND = re.compile(r"mise run ([A-Za-z0-9_][A-Za-z0-9_:-]*)")


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


def unknown(texts: dict[str, str], names: set[str]) -> list[str]:
    found = []
    for where, text in texts.items():
        for number, line in enumerate(text.split("\n"), 1):
            for match in COMMAND.finditer(line):
                if match.group(1) not in names:
                    found.append(
                        f"{where}:{number}: `mise run {match.group(1)}` is not a task"
                    )
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--self-test", action="store_true", help="prove the check can fail first"
    )
    args = parser.parse_args()

    names = task_names()
    if args.self_test and not unknown({"probe": "mise run no-such-task-xyz"}, names):
        raise SystemExit("self-test: an unknown task name was not reported")

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
