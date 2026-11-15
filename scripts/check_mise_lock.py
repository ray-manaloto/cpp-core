#!/usr/bin/env python3
"""Check that mise.lock can install every pinned tool on every locked platform.

Two checks, both read-only:

- every tool in .mise.toml's [tools] has a mise.lock entry at the pinned version;
- every conda dependency a platform entry names (`conda_deps`) has its own
  `[conda-packages.<platform>]` record with a URL and a checksum. A dangling one makes
  `mise install --locked` fail on that platform ("conda package ... not found in lockfile").

mise writes platform entries both as `[...platforms.<os>]` tables and as dotted keys
(`"platforms.macos-arm64" = {...}`); both forms are read.

`--self-test` runs the checks against a broken sample first, so a clean result means the
check can fail. `--install` also runs `mise install --locked` into an empty temporary data
directory, which downloads every tool and is slow: it is a task, not a hook.

Stdlib only. Exit status is 0 when the lock is whole and 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / ".mise.toml"
LOCK = REPO_ROOT / "mise.lock"


def platform_entries(entry: dict) -> dict[str, dict]:
    """The per-platform tables of one locked tool version, in either spelling."""
    found = dict(entry.get("platforms") or {})
    for key, value in entry.items():
        if key.startswith("platforms.") and isinstance(value, dict):
            found[key.split(".", 1)[1]] = value
    return found


def pinned_version(spec: object) -> str | None:
    if isinstance(spec, str):
        return spec
    if isinstance(spec, dict):
        return spec.get("version")
    return None


def problems(config: dict, lock: dict) -> list[str]:
    found: list[str] = []
    tools = lock.get("tools", {})
    packages = lock.get("conda-packages", {})

    for name, spec in config.get("tools", {}).items():
        want = pinned_version(spec)
        versions = [entry.get("version") for entry in tools.get(name, [])]
        if want not in versions:
            found.append(
                f"{name}: pinned {want}, mise.lock has {versions or 'no entry'}"
            )

    for name, entries in tools.items():
        for entry in entries:
            for platform, info in platform_entries(entry).items():
                for dep in info.get("conda_deps", []):
                    record = packages.get(platform, {}).get(dep)
                    if (
                        not record
                        or not record.get("url")
                        or not record.get("checksum")
                    ):
                        found.append(
                            f"{name}@{entry.get('version')} {platform}: conda_deps names {dep}, "
                            "which has no [conda-packages] record; run `mise lock` from a deleted "
                            "mise.lock"
                        )
    return found


def self_test() -> None:
    """The checks must fail on a lock that is known to be broken."""
    config = {"tools": {"clang-format": "1.0", "ruff": "2.0"}}
    lock = {
        "tools": {
            "clang-format": [
                {
                    "version": "1.0",
                    "platforms.macos-arm64": {"conda_deps": ["present", "dangling"]},
                }
            ]
        },
        "conda-packages": {"macos-arm64": {"present": {"url": "u", "checksum": "c"}}},
    }
    found = problems(config, lock)
    if not any("dangling" in line for line in found) or not any(
        "ruff" in line for line in found
    ):
        raise SystemExit(f"self-test: the checks missed a known-broken lock: {found}")


INSTALL_TIMEOUT_SECONDS = 1200


def isolated_env(root: Path) -> dict[str, str]:
    """An environment in which mise sees only this repository's config and writes only to root.

    Every inherited `MISE_*` variable is dropped (an inherited `MISE_INSTALLS_DIR` or
    `MISE_SHIMS_DIR` would send installs into the user's real tool directory), then the config,
    data, cache and state directories are pointed under root. `MISE_CONFIG_DIR` at an empty
    directory keeps the user's global config (and every global tool) out; `MISE_GLOBAL_CONFIG_FILE`
    alone does not. One run without it installed 160 global tools and hung compiling lua.

    The npm installer is a user setting, and it decides how mise.lock records npm tools; the
    user's own choice is passed through so the lock is installed the way it was written.
    """
    npm_installer = subprocess.run(
        ["mise", "settings", "get", "npm.package_manager"],
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout.strip()
    (root / "config").mkdir()
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("MISE_")
    }
    env.update(
        MISE_CONFIG_DIR=str(root / "config"),
        MISE_DATA_DIR=str(root / "data"),
        MISE_CACHE_DIR=str(root / "cache"),
        MISE_STATE_DIR=str(root / "state"),
        MISE_TRUSTED_CONFIG_PATHS=str(REPO_ROOT),
        MISE_NPM_PACKAGE_MANAGER=npm_installer,
    )
    return env


def current_tools(env: dict[str, str]) -> dict[str, list[dict]]:
    out = subprocess.run(
        ["mise", "ls", "--current", "--json"],
        check=True,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    ).stdout
    return json.loads(out)


def foreign_tools(env: dict[str, str], pinned: set[str]) -> list[str]:
    """Tools mise would load in this environment that .mise.toml does not pin."""
    return sorted(set(current_tools(env)) - pinned)


def installs_outside(env: dict[str, str], root: Path) -> list[str]:
    """Installed tools whose install path is not under root."""
    outside = []
    for name, versions in current_tools(env).items():
        for version in versions:
            path = version.get("install_path")
            if path and not Path(path).resolve().is_relative_to(root.resolve()):
                outside.append(f"{name}: {path}")
    return outside


def stop_group(process: subprocess.Popen) -> None:
    """End the installer's whole process group: TERM, a grace period, then KILL."""
    for sig, grace in ((signal.SIGTERM, 10), (signal.SIGKILL, 10)):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue
        # The leader is gone; a descendant may still hold the group, so the next signal
        # still goes out unless the group is empty.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def install_locked(pinned: set[str]) -> int:
    """Install only this repository's pins, from the lock, into empty directories."""
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        env = isolated_env(root)
        foreign = foreign_tools(env, pinned)
        if foreign:
            print(f"problem: refusing to install; mise would also load {foreign}")
            return 1
        # Its own process group, so every installer it starts can be ended with it.
        process = subprocess.Popen(
            ["mise", "install", "--locked"],
            cwd=REPO_ROOT,
            env=env,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=INSTALL_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            print(f"problem: mise install --locked ran over {INSTALL_TIMEOUT_SECONDS}s")
            code = 1
        finally:
            # Also on Ctrl-C and on a normal exit: nothing it started may outlive it.
            stop_group(process)
        outside = installs_outside(env, root)
        for line in outside:
            print(f"problem: installed outside the scratch directory: {line}")
        return 1 if outside else code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--self-test", action="store_true", help="prove the checks can fail first"
    )
    parser.add_argument(
        "--install", action="store_true", help="also install from the lock (slow)"
    )
    args = parser.parse_args()

    if args.self_test:
        self_test()
    with CONFIG.open("rb") as handle:
        config = tomllib.load(handle)
    with LOCK.open("rb") as handle:
        lock = tomllib.load(handle)

    found = problems(config, lock)
    for line in found:
        print(f"problem: {line}")
    if found:
        return 1
    print(f"mise.lock holds every pin: {len(config.get('tools', {}))} tools")
    if args.install:
        return install_locked(set(config.get("tools", {})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
