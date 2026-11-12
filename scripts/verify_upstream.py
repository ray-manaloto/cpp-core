#!/usr/bin/env python3
"""The vendored upstream copies, checked against their manifest.

`docs/cxx26-features-audit/upstream/README.md` is the human-readable provenance record: where
each file came from, at which ref, under which licence. This script is the machine-readable half
- `upstream/manifest.json` carries a sha256 for every vendored file, so that a copy that drifts
from the one the audit quotes is caught rather than discovered.

The check is local: it hashes the files that are in the tree. It does not fetch anything.

Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "docs" / "cxx26-features-audit" / "upstream" / "manifest.json"
UPSTREAM_DIR = REPO_ROOT / "docs" / "cxx26-features-audit" / "upstream"


def build_manifest() -> dict:
    """The manifest, derived from the files that are in the tree.

    The provenance - origin, ref, licence - is copied from `upstream/README.md`; the hashes are
    computed here.
    """
    entries = [
        {
            "path": "docs/cxx26-features-audit/upstream/ut/CMakeLists.txt",
            "origin": "https://github.com/stephenberry/ut",
            "ref": "dc65567be78febd265ca36c324e1c504512d4d74",
            "upstream_path": "CMakeLists.txt",
            "licence": "Boost Software License 1.0",
            "byte_identical_to_upstream": True,
        },
        {
            "path": "docs/cxx26-features-audit/upstream/ut/modules/ut.ixx",
            "origin": "https://github.com/stephenberry/ut",
            "ref": "dc65567be78febd265ca36c324e1c504512d4d74",
            "upstream_path": "modules/ut.ixx",
            "licence": "Boost Software License 1.0",
            "byte_identical_to_upstream": True,
        },
        {
            "path": "docs/cxx26-features-audit/upstream/stdx/ct_format.hpp",
            "origin": "https://github.com/intel/cpp-std-extensions",
            "ref": "94546c5a9122b99dc671cbefd7cfec168108febe",
            "upstream_path": "include/stdx/ct_format.hpp",
            "licence": "Boost Software License 1.0",
            "byte_identical_to_upstream": None,
        },
        {
            "path": "docs/cxx26-features-audit/upstream/stdx/detail/fmt.hpp",
            "origin": "https://github.com/intel/cpp-std-extensions",
            "ref": "94546c5a9122b99dc671cbefd7cfec168108febe",
            "upstream_path": "include/stdx/detail/fmt.hpp",
            "licence": "Boost Software License 1.0",
            "byte_identical_to_upstream": None,
        },
        {
            "path": "docs/cxx26-features-audit/upstream/stdx/COPYRIGHT",
            "origin": "https://github.com/intel/cpp-std-extensions",
            "ref": "94546c5a9122b99dc671cbefd7cfec168108febe",
            "upstream_path": "share/intel-cpp-std-extensions/copyright",
            "licence": "Boost Software License 1.0",
            "byte_identical_to_upstream": None,
        },
        {
            "path": "docs/cxx26-features-audit/upstream/fmt/base.h",
            "origin": "https://github.com/fmtlib/fmt",
            "ref": "208219daff58f2a7438f6931cc2ddc358acf33ef",
            "upstream_path": "include/fmt/base.h",
            "licence": "MIT",
            "byte_identical_to_upstream": True,
        },
        {
            "path": "docs/cxx26-features-audit/upstream/fmt/compile.h",
            "origin": "https://github.com/fmtlib/fmt",
            "ref": "208219daff58f2a7438f6931cc2ddc358acf33ef",
            "upstream_path": "include/fmt/compile.h",
            "licence": "MIT",
            "byte_identical_to_upstream": True,
        },
        {
            "path": "docs/cxx26-features-audit/upstream/fmt/format.h",
            "origin": "https://github.com/fmtlib/fmt",
            "ref": "208219daff58f2a7438f6931cc2ddc358acf33ef",
            "upstream_path": "include/fmt/format.h",
            "licence": "MIT",
            "byte_identical_to_upstream": False,
            "note": "vcpkg's backport of upstream PR #4813 is applied; "
            "see upstream/README.md and upstream/fmt/backport-4813.patch",
        },
        {
            "path": "docs/cxx26-features-audit/upstream/fmt/LICENSE",
            "origin": "https://github.com/fmtlib/fmt",
            "ref": "208219daff58f2a7438f6931cc2ddc358acf33ef",
            "upstream_path": "LICENSE",
            "licence": "MIT",
            "byte_identical_to_upstream": True,
        },
        {
            "path": "docs/cxx26-features-audit/upstream/fmt/backport-4813.patch",
            "origin": "vcpkg",
            "ref": "245d37306671ea67d8f313081a81aae8079f8916",
            "upstream_path": "downloads/fmt-backport-4813.patch",
            "licence": "MIT",
            "byte_identical_to_upstream": None,
        },
    ]

    files = []
    for entry in entries:
        path = REPO_ROOT / entry["path"]
        data = path.read_bytes()
        record = dict(entry)
        record["sha256"] = hashlib.sha256(data).hexdigest()
        record["bytes"] = len(data)
        files.append(record)

    return {
        "schema": 1,
        "generated_by": "scripts/verify_upstream.py",
        "provenance": "docs/cxx26-features-audit/upstream/README.md",
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite the manifest from the files that are in the tree",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the manifest is stale or a file has changed",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest()
    rendered = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    if args.write:
        MANIFEST.write_text(rendered, encoding="utf-8")
        print(f"wrote {MANIFEST.relative_to(REPO_ROOT)} ({len(manifest['files'])} files)")
        return 0

    if not MANIFEST.exists():
        print(f"missing {MANIFEST.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1

    problems = []
    if MANIFEST.read_text(encoding="utf-8") != rendered:
        problems.append(
            f"{MANIFEST.relative_to(REPO_ROOT)} is stale - run "
            f"`mise run audit:upstream --write`"
        )

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

    # A file in the tree that the manifest does not know about is drift too. The manifest and the
    # provenance record are the manifest's own companions, not vendored sources.
    known = {entry["path"] for entry in manifest["files"]}
    for path in sorted(UPSTREAM_DIR.rglob("*")):
        if path.is_dir() or path.name in {"README.md", "manifest.json"}:
            continue
        relative = str(path.relative_to(REPO_ROOT))
        if relative not in known:
            problems.append(f"{relative} is vendored but not in the manifest")

    if problems:
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"the manifest matches: {len(manifest['files'])} vendored files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
