#!/usr/bin/env python3
"""The overlay ports' pins, against their upstreams' current tips.

The root README says the overlay ports are "pinned to the latest upstream commit". That is true
today - and nothing checks it. This script reads each port's `REF` and `HEAD_REF` and, with
`--network`, compares the `REF` against the tip of the branch it names.

A port whose `REF` is behind its upstream's tip is not wrong - it is *drifting*, and the
question is whether the project wants to move. The four Intel ports track a `main` branch, so
they drift by construction; `ut` pins an immutable tag, which is the shape the others should
follow.

Stdlib only. The network check uses `git ls-remote` and needs no compiler.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PORTS_DIR = REPO_ROOT / "ports"

FROM_GITHUB_RE = re.compile(r"vcpkg_from_github\((.*?)\n\)", re.DOTALL)
FIELD_RE = re.compile(r"^\s*(REPO|REF|HEAD_REF|SHA512)\s+(\S+)\s*$", re.MULTILINE)


def read_port(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = FROM_GITHUB_RE.search(text)
    fields = {}
    if match:
        for key, value in FIELD_RE.findall(match.group(1)):
            fields[key] = value
    return fields


def ls_remote(url: str, ref: str, timeout: int = 30) -> str | None:
    """The tip of `ref` at `url`, or None if it cannot be read.

    `git ls-remote <url> <pattern>` prints the full ref name - `refs/heads/main`, not `main` - so
    the pattern is matched against the tail of the name.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", url, ref],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.split("\n"):
        parts = line.split()
        if len(parts) != 2:
            continue
        name = parts[1]
        if name == ref or name.endswith("/" + ref):
            return parts[0]
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--network",
        action="store_true",
        help="compare each REF against its upstream's current tip",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="print the pins and stop (the default when the network is not asked for)",
    )
    args = parser.parse_args(argv)

    ports = []
    for portfile in sorted(PORTS_DIR.glob("*/portfile.cmake")):
        fields = read_port(portfile)
        if not fields:
            continue
        ports.append((portfile.parent.name, fields))

    if not ports:
        print("no overlay ports found", file=sys.stderr)
        return 1

    print(f"{len(ports)} overlay ports\n")
    drifting = []
    unreachable = []

    for name, fields in ports:
        repo = fields.get("REPO", "?")
        ref = fields.get("REF", "?")
        head_ref = fields.get("HEAD_REF", "-")
        url = f"https://github.com/{repo}"
        print(f"  {name}")
        print(f"    repo     {repo}")
        print(f"    ref      {ref}")
        print(f"    head ref {head_ref}")

        if args.offline or not args.network:
            continue

        target = head_ref if head_ref != "-" else ref
        tip = ls_remote(url, target)
        if tip is None:
            unreachable.append(name)
            print(
                "    tip      (could not be read - no network, or the ref does not exist)"
            )
            continue
        state = "at the tip" if tip == ref else "BEHIND the tip"
        print(f"    tip      {tip} ({state})")
        if tip != ref:
            drifting.append((name, ref, tip))

    if args.offline or not args.network:
        print(
            "\n(the network check was not run - pass --network to compare against upstream)"
        )
        return 0

    print()
    if unreachable:
        print(
            f"{len(unreachable)} port(s) could not be checked "
            f"(no network, or the ref does not exist): {', '.join(unreachable)}"
        )
    if drifting:
        print(f"{len(drifting)} port(s) are behind their upstream's tip:")
        for name, ref, tip in drifting:
            print(f"  {name}: {ref} -> {tip}")
        print(
            "\nA port behind its tip is not wrong. It is drifting: the question is whether the "
            "project wants\nto move, and the answer has to account for what the bump breaks."
        )
        return 0
    if unreachable:
        print("nothing could be compared - the pins are listed above")
        return 0
    print("every port's REF is at its upstream's tip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
