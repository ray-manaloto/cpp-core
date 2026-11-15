#!/usr/bin/env python3
"""Merge a pull request only when every gate in AGENTS.md's Shipping fact holds.

The gates, in order:

1. The pull request is open and targets `main`.
2. Its head commit is checked out, clean, in a worktree of this repository.
3. That worktree's `user.email` is the noreply address of the account `gh` is logged in as.
4. The pinned Codex reviewer approved the pull request's title and body at that head
   (`repotools pr-approved`). The body is GitHub's copy with CodeRabbit's bounded summary block
   removed; any other text added after the approval fails the gate.
5. `hk check --all` passes in that worktree.

Before merging it checks again that the worktree is still clean at the head and that the pull
request's head, base, title and body have not changed, then merges with
`--merge --match-head-commit <head> --author-email <user.email>` and checks that GitHub authored
the merge commit with that email. `--dry-run` checks the gates and stops.

Limits. The approval gate reads the reviewer pane's session log, a plain file the author's own
tools can reach: it catches a stale, edited or unreviewed head, not a forged approval. It checks
the approval of the pull request text at the head, not each commit's own approval, which is
given before each commit. The final check and the merge are not atomic; `--match-head-commit`
covers the head, not a title or body edited in between. The advisory CI run is looked at by hand.

Exit status is 0 when the gates pass (and the merge, unless `--dry-run`, succeeded), 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PR_FIELDS = "state,baseRefName,headRefOid,title,body"
# CodeRabbit inserts its summary into the body after the author opens the pull request.
CODERABBIT_START = (
    "<!-- This is an auto-generated comment: release notes by coderabbit.ai -->"
)
CODERABBIT_END = (
    "<!-- end of auto-generated comment: release notes by coderabbit.ai -->"
)


class GateError(Exception):
    pass


def run(
    args: list[str], cwd: Path, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, check=False, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise GateError(
            f"`{' '.join(args)}` failed:\n{result.stdout}{result.stderr}".rstrip()
        )
    return result


def author_body(body: str) -> str:
    """GitHub's body without CodeRabbit's block, when that block is the whole tail.

    Text outside the block, before or after it, is kept, so an edit made after the approval
    still fails the approval check.
    """
    before, start, rest = body.partition(CODERABBIT_START)
    if not start:
        return body
    _, end, after = rest.partition(CODERABBIT_END)
    if not end or after.strip():
        return body
    return before.rstrip("\n") + "\n"


def view(number: int) -> dict[str, str]:
    out = run(["gh", "pr", "view", str(number), "--json", PR_FIELDS], REPO_ROOT).stdout
    return json.loads(out)


def worktree_at(sha: str) -> Path:
    listing = run(["git", "worktree", "list", "--porcelain"], REPO_ROOT).stdout
    for block in listing.split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        if fields.get("HEAD") == sha:
            return Path(fields["worktree"])
    raise GateError(
        f"no worktree has the head commit {sha[:7]} checked out; check out the pull request"
        " in its own worktree, where the reviewer pane is pinned"
    )


def check_tree(tree: Path, sha: str) -> None:
    head = run(["git", "rev-parse", "HEAD"], tree).stdout.strip()
    if head != sha:
        raise GateError(f"the worktree {tree.name} moved from {sha[:7]} to {head[:7]}")
    dirty = run(["git", "status", "--porcelain"], tree).stdout
    if dirty:
        raise GateError(f"the worktree {tree.name} is not clean:\n{dirty}".rstrip())


def account_noreply() -> str:
    user = json.loads(run(["gh", "api", "user"], REPO_ROOT).stdout)
    return f"{user['id']}+{user['login']}@users.noreply.github.com"


def gates(number: int) -> tuple[dict[str, str], str, Path]:
    pr = view(number)
    if pr["state"] != "OPEN":
        raise GateError(f"#{number} is {pr['state']}, not OPEN")
    if pr["baseRefName"] != "main":
        raise GateError(f"#{number} targets {pr['baseRefName']}, not main")
    sha = pr["headRefOid"]
    print(f"ok    #{number} is open against main, head {sha[:7]}")

    tree = worktree_at(sha)
    check_tree(tree, sha)
    print(f"ok    worktree {tree.name} is clean at the head")

    email = run(["git", "config", "user.email"], tree).stdout.strip()
    if email != account_noreply():
        raise GateError(
            f"user.email in {tree.name} is not the noreply address of the account gh uses"
        )
    print("ok    user.email is the merging account's noreply address")

    with tempfile.TemporaryDirectory() as scratch:
        body_file = Path(scratch) / "body.md"
        body_file.write_text(author_body(pr["body"]), encoding="utf-8")
        args = ["repotools", "pr-approved", "--title", pr["title"]]
        run([*args, "--body-file", str(body_file)], tree)
    print("ok    the reviewer approved the pull request text at the head")

    hk = run(["hk", "check", "--all"], tree, check=False)
    if hk.returncode != 0:
        tail = "\n".join((hk.stdout + hk.stderr).splitlines()[-20:])
        raise GateError(f"`hk check --all` failed in {tree.name}:\n{tail}")
    print("ok    hk check --all passes")

    check_tree(tree, sha)
    if view(number) != pr:
        raise GateError(
            f"#{number} changed on GitHub while the gates ran; run it again"
        )
    print("ok    nothing changed while the gates ran")
    return pr, email, tree


def merge(number: int, sha: str, email: str) -> None:
    merge_args = ["gh", "pr", "merge", str(number), "--merge"]
    merge_args += ["--match-head-commit", sha, "--author-email", email]
    run(merge_args, REPO_ROOT)
    merged = json.loads(
        run(
            ["gh", "pr", "view", str(number), "--json", "mergeCommit"], REPO_ROOT
        ).stdout
    )["mergeCommit"]["oid"]
    commit = f"repos/{{owner}}/{{repo}}/commits/{merged}"
    author = run(
        ["gh", "api", commit, "--jq", ".commit.author.email"], REPO_ROOT
    ).stdout.strip()
    if author != email:
        raise GateError(
            f"merged as {merged[:7]}, but its author email is not user.email"
        )
    print(f"ok    merged #{number} as {merged[:7]}, authored with user.email")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("number", type=int, help="the pull request number")
    parser.add_argument(
        "--dry-run", action="store_true", help="check the gates, do not merge"
    )
    args = parser.parse_args()
    try:
        pr, email, _ = gates(args.number)
        sha = pr["headRefOid"]
        if args.dry_run:
            print(
                f"dry run: every gate passes; would merge #{args.number} at {sha[:7]}"
            )
            return 0
        merge(args.number, sha, email)
    except GateError as error:
        print(f"FAIL  {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
