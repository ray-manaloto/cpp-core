#!/usr/bin/env python3
"""Print the "Repository Problems" lines from every saved revision of the Dependency Dashboard.

GitHub keeps each revision Renovate saves to the dashboard issue, so the edit history shows when
a warning appeared and when it went away. A run that leaves the dashboard unchanged saves no
revision, so a run is confirmed only by its log on developer.mend.io, which also names the
branch that raised a warning (the WARN line's `branch=` field). Reads only; needs an
authenticated `gh`.

    python3 scripts/renovate_problems.py [--issue N] [--since 2026-11-16T00:00:00Z]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime

QUERY = """
query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      title
      userContentEdits(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes { editedAt diff }
      }
    }
  }
}
"""

HEADING = "## Repository Problems"


def gh(*args: str) -> str:
    done = subprocess.run(["gh", *args], check=False, capture_output=True, text=True)
    if done.returncode != 0:
        sys.exit(f"renovate:problems: gh {args[0]} failed: {done.stderr.strip()}")
    return done.stdout


def problems(body: str) -> list[str]:
    """The bullet lines under the Repository Problems heading, or [] when there is none."""
    lines = body.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == HEADING)
    except StopIteration:
        return []
    found = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.lstrip().startswith("- "):
            found.append(line.strip()[2:])
    return found


def revisions(owner: str, name: str, number: int) -> list[tuple[str, str | None]]:
    edits: list[tuple[str, str | None]] = []
    after = None
    while True:
        args = [
            "api",
            "graphql",
            "-f",
            f"query={QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
        ]
        args += ["-F", f"number={number}"]
        if after:
            args += ["-F", f"after={after}"]
        issue = json.loads(gh(*args))["data"]["repository"]["issue"]
        if issue is None:
            sys.exit(f"renovate:problems: no issue #{number} in {owner}/{name}")
        page = issue["userContentEdits"]
        edits += [(n["editedAt"], n["diff"]) for n in page["nodes"]]
        if not page["pageInfo"]["hasNextPage"]:
            return sorted(edits, key=lambda edit: when(edit[0]))
        after = page["pageInfo"]["endCursor"]


def when(text: str) -> datetime:
    """An ISO-8601 time with a zone, such as GitHub's editedAt (2026-11-16T13:00:51Z)."""
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError(f"{text!r} has no time zone; end it with Z or +00:00")
    return moment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--issue", type=int, default=12, help="dashboard issue number (default 12)"
    )
    parser.add_argument(
        "--since", default="", help="only revisions at or after this ISO-8601 UTC time"
    )
    args = parser.parse_args()
    try:
        since = when(args.since) if args.since else None
    except ValueError as error:
        parser.error(f"--since: {error}")
    owner, name = gh(
        "repo", "view", "--json", "owner,name", "--jq", '.owner.login + " " + .name'
    ).split()
    shown = 0
    for edited_at, body in revisions(owner, name, args.issue):
        if since and when(edited_at) < since:
            continue
        shown += 1
        if body is None:
            print(f"{edited_at}  (revision text not available from GitHub)")
            continue
        found = problems(body)
        print(f"{edited_at}  {'(none)' if not found else found[0]}")
        for line in found[1:]:
            print(f"{'':22}{line}")
    if shown == 0:
        print(f"no revisions of #{args.issue} at or after {args.since!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
