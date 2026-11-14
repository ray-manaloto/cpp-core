#!/usr/bin/env python3
"""The project's measurable qualities, with a baseline and a delta.

"Measure properly" means two things: the number is **reproducible** (the same command gives the
same answer), and the number has a **baseline** (so a change is visible as a delta rather than as
an opinion).

This measures the classes of quality that can be measured **without a compiler**:

- the library's shape - code lines per file, and how much of it is hand-rolled;
- the interface discipline - what the module interface is allowed to include;
- the public API surface, and how much of it the tests exercise at source level;
- the **audit's own coverage** - which lines of the library the audit has actually looked at,
  which is what says where the next research should go;
- the dependency closure - how many third-party headers the library actually reaches.

What it cannot measure, and says so: coverage percentage, runtime cost, binary size, and
sanitizer cleanliness. Those need the build lane, and they are named in the output with the
command that would produce each.

The baseline lives in `docs/cxx26-features-audit/measurements.json` and is committed, so a
metric that gets worse is visible in a diff.

Stdlib only. No compiler, no CMake, no network.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from citations import (
    audit_citations,
    library_files,
    physical_lines,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "docs" / "cxx26-features-audit"
MEASUREMENTS = AUDIT_DIR / "measurements.json"


def strip_comments(text: str) -> str:
    """Remove the comments, keeping the code and the line structure.

    A block comment on a line of its own is a comment line. A block comment followed by code on
    the same line is *not* - the code counts. String and character literals are respected, so a
    `//` inside a literal is not a comment. The project uses no raw string literals.
    """
    out: list[str] = []
    in_block = False
    in_string = False
    in_char = False
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        following = text[index + 1] if index + 1 < length else ""
        if in_block:
            if char == "*" and following == "/":
                in_block = False
                index += 2
                # A space, so `/*x*/code` does not become `code` glued to what came before.
                out.append(" ")
                continue
            if char == "\n":
                out.append("\n")
            index += 1
            continue
        if not in_string and not in_char:
            if char == "/" and following == "*":
                in_block = True
                index += 2
                continue
            if char == "/" and following == "/":
                while index < length and text[index] != "\n":
                    index += 1
                continue
        if char == '"' and not in_char:
            in_string = not in_string
        elif char == "'" and not in_string:
            in_char = not in_char
        elif char == "\n":
            in_string = False
            in_char = False
        out.append(char)
        index += 1
    return "".join(out)


def code_lines(path: Path) -> int:
    """Lines of code: not blank, not a comment."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return sum(1 for line in strip_comments(text).split("\n") if line.strip())


def module_interface() -> Path:
    return REPO_ROOT / "modules" / "logging" / "logging.cppm"


def public_api() -> list[str]:
    """The functions the module interface exports."""
    text = module_interface().read_text(encoding="utf-8")
    names = set()
    for match in re.finditer(
        r"^\s*(?:\[\[nodiscard\]\]\s*)?auto\s+(\w+)\s*\(", text, re.MULTILINE
    ):
        names.add(match.group(1))
    return sorted(names)


def interface_discipline() -> dict:
    """What the module interface is allowed to include, and what it actually includes."""
    text = module_interface().read_text(encoding="utf-8")
    includes = re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', text, re.MULTILINE)
    standard = [
        name for name in includes if "/" not in name and not name.endswith(".hpp")
    ]
    project = [name for name in includes if name.endswith(".hpp")]
    return {
        "includes": includes,
        "standard_library_includes": standard,
        "project_includes": project,
    }


def tested_api(api: list[str]) -> dict:
    """Which of the public API the test file calls. Source level, not coverage."""
    test = REPO_ROOT / "tests" / "logging_test.cpp"
    text = test.read_text(encoding="utf-8")
    called = [name for name in api if re.search(rf"\b{re.escape(name)}\s*\(", text)]
    return {"called": sorted(called), "not_called": sorted(set(api) - set(called))}


INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', re.MULTILINE)
HEADER_SUFFIXES = {".h", ".hpp", ".hxx", ".hh", ".ipp", ".tpp", ".inl"}

# The compiler's own record of what it included. A Ninja tree writes one depfile per
# translation unit; it is the ground truth for the include closure, and it is an artifact of a
# build that already happened - reading it does not build anything.
DEPFILE_GLOB = "*.ddi.d"
HEADER_TOKEN = re.compile(r"[^\s:\\]+\.(?:h|hpp|hxx|hh|ipp|tpp|inl)")


def build_trees() -> list[Path]:
    return sorted(path for path in (REPO_ROOT / "build").glob("*") if path.is_dir())


def depfile_closure(tree: Path) -> dict | None:
    """The third-party headers the compiler recorded, for one build tree."""
    depfiles = sorted(tree.rglob(DEPFILE_GLOB))
    if not depfiles:
        return None

    install = tree / "vcpkg_installed"
    reached: set[str] = set()
    per_unit: dict[str, int] = {}
    for depfile in depfiles:
        text = depfile.read_text(encoding="utf-8", errors="replace")
        headers = {
            token for token in HEADER_TOKEN.findall(text) if "vcpkg_installed" in token
        }
        reached.update(headers)
        unit = depfile.name
        per_unit[unit] = len(headers)

    packages: dict[str, int] = {}
    for header in reached:
        parts = Path(header).parts
        if "vcpkg_installed" not in parts:
            continue
        index = parts.index("vcpkg_installed")
        # <tree>/vcpkg_installed/<triplet>/include/<package>/<header>
        package = parts[index + 3] if index + 3 < len(parts) else "(root)"
        packages[package] = packages.get(package, 0) + 1

    roots = sorted(install.glob("*/include"))
    installed = 0
    installed_packages: list[str] = []
    if roots:
        installed = sum(
            1
            for path in roots[0].rglob("*")
            if path.is_file() and path.suffix.lower() in HEADER_SUFFIXES
        )
        installed_packages = sorted(
            path.name for path in roots[0].iterdir() if path.is_dir()
        )
    return {
        "tree": tree.name,
        "translation_units": len(depfiles),
        "reached_headers": len(reached),
        "installed_headers": installed,
        "installed_packages": installed_packages,
        "packages": dict(sorted(packages.items(), key=lambda item: -item[1])),
    }


def install_root() -> Path | None:
    candidates = sorted((REPO_ROOT / "build").glob("*/vcpkg_installed/*/include"))
    return candidates[0] if candidates else None


def resolved_closure(root: Path) -> dict:
    """The include closure, computed by resolving the project's own `#include` lines.

    This is the fallback, and it is *not* the same number as the compiler's record: it starts
    from the project's headers and follows the includes it can see, so it misses whatever is
    pulled in by the translation units it did not start from. The harness reports both, and
    says which is which.
    """
    project_sources = [
        REPO_ROOT / "include" / "cpp-core" / "logging" / "cib_quill.hpp",
        REPO_ROOT / "include" / "cpp-core" / "logging" / "internal.hpp",
        REPO_ROOT / "include" / "cpp-core" / "logging" / "quill_logger.hpp",
        REPO_ROOT / "modules" / "logging" / "logging.cppm",
        REPO_ROOT / "modules" / "logging" / "format.hpp",
    ]

    def resolve(name: str, current: Path) -> Path | None:
        candidates = [root / name]
        if current is not None:
            candidates.append(current.parent / name)
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    seen: set[Path] = set()
    queue: list[tuple[Path, Path | None]] = [(path, None) for path in project_sources]
    reached: set[Path] = set()

    while queue:
        current, _parent = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        try:
            text = current.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name in INCLUDE_RE.findall(text):
            if name.startswith("cpp-core/"):
                resolved = REPO_ROOT / "include" / name
                if resolved.is_file():
                    queue.append((resolved, current))
                continue
            resolved = resolve(name, current)
            if resolved is None:
                continue
            queue.append((resolved, current))
            if str(resolved).startswith(str(root)):
                reached.add(resolved)

    packages: dict[str, int] = {}
    for resolved in reached:
        relative = resolved.relative_to(root)
        package = relative.parts[0] if len(relative.parts) > 1 else "(root)"
        packages[package] = packages.get(package, 0) + 1

    # Headers only. The install tree also carries sources, licence files and cmake glue, and
    # counting those against "headers reached" would compare two different things.
    installed_headers = {
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in HEADER_SUFFIXES
    }
    return {
        "installed_headers": len(installed_headers),
        "installed_files": sum(1 for path in root.rglob("*") if path.is_file()),
        "reached_headers": len(reached),
        "packages": dict(sorted(packages.items(), key=lambda item: -item[1])),
    }


def include_closure() -> dict:
    """The dependency closure, measured from the compiler's own record.

    The primary source is the depfiles the last build wrote: one per translation unit, listing
    every header the compiler actually opened. Reading a build artifact does not build
    anything - it is evidence about a build that already happened.

    Every build tree is read, and the numbers are cross-checked: two compilers agreeing on the
    closure is a stronger statement than either one alone.

    The fallback, for a tree with no depfiles, is to resolve the project's own `#include`
    lines. It is reported separately and labelled, because it is not the same measurement.
    """
    closures = []
    for tree in build_trees():
        closure = depfile_closure(tree)
        if closure is not None:
            closures.append(closure)

    root = install_root()
    resolved = resolved_closure(root) if root is not None else None

    if not closures:
        if resolved is None:
            return {"available": False}
        return {
            "available": True,
            "source": "resolved from the project's include lines (no build artifacts present)",
            "per_tree": [],
            **resolved,
        }

    counts = {closure["reached_headers"] for closure in closures}
    packages = max(closures, key=lambda closure: closure["reached_headers"])["packages"]
    # Not every build tree carries an install tree - the clang coverage tree does not - so the
    # installed count is the largest one any tree can see.
    installed = max((closure["installed_headers"] for closure in closures), default=0)
    installed_packages = max(
        (closure["installed_packages"] for closure in closures),
        key=len,
        default=[],
    )
    unreached = sorted(set(installed_packages) - set(packages))
    if not installed and resolved is not None:
        installed = resolved["installed_headers"]
    return {
        "available": True,
        "source": "the depfiles the last build wrote",
        "per_tree": closures,
        "trees_measured": len(closures),
        "trees_agreeing": len(counts) == 1,
        "distinct_closure_sizes": len(counts),
        "reached_headers": closures[0]["reached_headers"],
        "installed_headers": installed,
        "installed_packages": installed_packages,
        "unreached_packages": unreached,
        "packages": packages,
        "resolved_fallback": resolved,
    }


def macros() -> dict:
    """The macros the project defines, and the macro invocations it makes.

    The `CIB_*` macros the project uses are **not its own** - they come from Intel's `cib`
    package. The project defines no macros at all, which is the point of parts 6 and 15.
    """
    defined = []
    call_sites = []
    for path in library_files():
        text = path.read_text(encoding="utf-8")
        defined.extend(re.findall(r"^\s*#\s*define\s+(\w+)", text, re.MULTILINE))
        for number, line in enumerate(text.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            for name in re.findall(r"\bCIB_\w+", stripped):
                call_sites.append(f"{path.relative_to(REPO_ROOT)}:{number} {name}")
    return {
        "defined_by_the_project": sorted(set(defined)),
        "cib_call_sites": len(call_sites),
        "cib_call_site_list": sorted(call_sites),
    }


def measure() -> dict:
    files = library_files()
    per_file = {str(path.relative_to(REPO_ROOT)): code_lines(path) for path in files}
    total = sum(per_file.values())

    formatter = per_file.get("modules/logging/format.hpp", 0)
    interface = per_file.get("modules/logging/logging.cppm", 0)
    test_lines = per_file.get("tests/logging_test.cpp", 0)

    api = public_api()
    tested = tested_api(api)

    citations, whole_files = audit_citations()
    citation_totals = {}
    for relative, lines in citations.items():
        path = REPO_ROOT / relative
        if not path.exists():
            continue
        # The numerator and the denominator have to be the same unit: physical source lines.
        # A cited line is a line someone looked at - whether it is code, a comment or a blank.
        source_lines = physical_lines(
            path.read_text(encoding="utf-8", errors="replace")
        )
        citation_totals[relative] = {
            "source_lines": source_lines,
            "cited_lines": len([line for line in lines if 1 <= line <= source_lines]),
            "whole_file_cited": relative in whole_files,
        }
    # A file cited only as a path has been looked at; a file cited with line numbers has been
    # read. Both are credited to the coverage, but the depth is reported separately.
    for relative in whole_files:
        path = REPO_ROOT / relative
        if not path.exists() or relative in citation_totals:
            continue
        source_lines = physical_lines(
            path.read_text(encoding="utf-8", errors="replace")
        )
        citation_totals[relative] = {
            "source_lines": source_lines,
            "cited_lines": 0,
            "whole_file_cited": True,
        }
    # The library is the set of files, not a prefix: `modules/CMakeLists.txt` is a build file
    # that happens to live under `modules/`.
    library_set = {str(path.relative_to(REPO_ROOT)) for path in files}
    library_total = sum(
        physical_lines(
            (REPO_ROOT / relative).read_text(encoding="utf-8", errors="replace")
        )
        for relative in library_set
    )
    library_cited = sum(
        entry["cited_lines"]
        for relative, entry in citation_totals.items()
        if relative in library_set
    )
    library_whole_file = sum(
        entry["source_lines"]
        for relative, entry in citation_totals.items()
        if relative in library_set and entry["whole_file_cited"]
    )
    library_seen = min(library_cited + library_whole_file, library_total)

    discipline = interface_discipline()
    return {
        "schema": 1,
        "generated_by": "scripts/measure.py",
        "library": {
            "files": len(files),
            "code_lines": total,
            "per_file": per_file,
            "hand_rolled_formatter_lines": formatter,
            "hand_rolled_formatter_share": round(formatter / total, 3) if total else 0,
            "module_interface_lines": interface,
            "test_lines": test_lines,
            "test_to_library_ratio": round(test_lines / total, 3) if total else 0,
        },
        "interface": {
            "standard_library_includes": len(discipline["standard_library_includes"]),
            "standard_library_include_names": discipline["standard_library_includes"],
            "project_includes": discipline["project_includes"],
        },
        "api": {
            "public_functions": len(api),
            "names": api,
            "tested_at_source_level": tested["called"],
            "not_tested_at_source_level": tested["not_called"],
        },
        "audit_coverage": {
            "library_source_lines": library_total,
            "library_lines_cited_specifically": library_cited,
            "library_lines_cited_whole_file": library_whole_file,
            "library_lines_seen": library_seen,
            "specific_share": round(library_cited / library_total, 3)
            if library_total
            else 0,
            "seen_share": round(library_seen / library_total, 3)
            if library_total
            else 0,
            "per_file": dict(sorted(citation_totals.items())),
        },
        "dependencies": include_closure(),
        "macros": macros(),
    }


def flatten(value, prefix: str = "") -> dict:
    """The scalar leaves, for comparison."""
    out = {}
    if isinstance(value, dict):
        for key, item in value.items():
            out.update(flatten(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        out[prefix] = len(value)
    else:
        out[prefix] = value
    return out


# ------------------------------------------------------------------------------------- the bar

ACCEPTANCE = AUDIT_DIR / "acceptance.json"


def acceptance_metrics(current: dict) -> dict:
    """The metrics the acceptance bar names, read out of the measurement.

    The bar holds thresholds, never observations, so every value here comes from the tree.
    """
    library = current["library"]
    interface = current["interface"]
    api = current["api"]
    coverage = current["audit_coverage"]
    dependencies = current["dependencies"]
    macros = current["macros"]

    metrics = {
        "interface.standard_library_includes": interface["standard_library_includes"],
        "macros.defined_by_the_project": len(macros["defined_by_the_project"]),
        "api.exported_functions": api["public_functions"],
        "api.exported_functions_untested": len(api["not_tested_at_source_level"]),
        "audit.read_coverage_share": coverage["specific_share"],
        "audit.seen_coverage_share": coverage["seen_share"],
        "library.hand_rolled_formatter_share": library["hand_rolled_formatter_share"],
        "library.hand_rolled_formatter_lines": library["hand_rolled_formatter_lines"],
        "library.test_to_library_ratio": library["test_to_library_ratio"],
        "library.code_lines": library["code_lines"],
    }
    if dependencies.get("available"):
        metrics["dependencies.reached_headers"] = dependencies["reached_headers"]
        metrics["dependencies.installed_headers"] = dependencies["installed_headers"]
        metrics["dependencies.unreached_packages"] = len(
            dependencies["unreached_packages"]
        )
        metrics["dependencies.build_trees_measured"] = dependencies["trees_measured"]
        metrics["dependencies.distinct_closure_sizes"] = dependencies[
            "distinct_closure_sizes"
        ]
    return metrics


def check_acceptance(current: dict) -> dict:
    """Evaluate the acceptance bar against the tree.

    A violation is a constraint that is measurable and not met. A deferred metric is one that
    cannot be measured here; it is reported, never failed.
    """
    if not ACCEPTANCE.exists():
        return {
            "violations": [
                f"missing {relative_to_repo(ACCEPTANCE)} - the bar is a standard; write it down"
            ],
            "satisfied": [],
            "targets": [],
            "deferred": [],
        }
    bar = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    metrics = acceptance_metrics(current)

    violations: list[str] = []
    satisfied: list[str] = []
    targets: list[str] = []
    deferred: list[str] = []

    for constraint in bar.get("constraints", []):
        name = constraint["metric"]
        kind = constraint["kind"]
        threshold = constraint["threshold"]
        if name not in metrics:
            deferred.append(
                f"{name:<40} not measurable here (it depends on build artifacts)"
            )
            continue
        observed = metrics[name]
        if kind == "floor" and observed < threshold:
            violations.append(f"{name}: {observed} is below the floor of {threshold}")
        elif kind == "ceiling" and observed > threshold:
            violations.append(f"{name}: {observed} is above the ceiling of {threshold}")
        else:
            satisfied.append(f"{name:<40} {observed} {kind} {threshold} - met")

    for target in bar.get("targets", []):
        name = target["metric"]
        if name not in metrics:
            targets.append(f"{name:<40} not measurable here")
            continue
        observed = metrics[name]
        direction = target["direction"]
        if direction == "down":
            mark = "ok" if observed <= target["value"] else "worse"
        else:
            mark = "ok" if observed >= target["value"] else "worse"
        targets.append(
            f"{name:<40} {observed} (target: {direction} from {target['value']}) - {mark}"
        )

    for entry in bar.get("deferred", []):
        threshold = entry.get("threshold")
        if threshold is None:
            shown = "threshold set at the first reading"
        elif entry["kind"] == "floor" and threshold <= 1.0 and threshold >= 0.0:
            shown = f"floor {threshold:.0%}"
        else:
            shown = f"{entry['kind']} {threshold}"
        deferred.append(
            f"{entry['metric']:<40} not measurable here - {shown} - {entry['command']}"
        )

    return {
        "violations": violations,
        "satisfied": satisfied,
        "targets": targets,
        "deferred": deferred,
    }


def relative_to_repo(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def print_acceptance(current: dict) -> None:
    report = check_acceptance(current)
    print(
        "\nTHE ACCEPTANCE BAR - what the project must not lose, and where it is headed"
    )
    if report["violations"]:
        print(f"  {len(report['violations'])} VIOLATION(S):")
        for violation in report["violations"]:
            print(f"    {violation}")
    else:
        print("  every constraint holds")
    print("  the constraints:")
    for entry in report["satisfied"]:
        print(f"    {entry}")
    print("  the targets - direction of travel, not gates:")
    for target in report["targets"]:
        print(f"    {target}")
    print("  the deferred metrics - named with the command that would produce each:")
    for entry in report["deferred"]:
        print(f"    {entry}")


# The sections that are derived from the source tree alone. They are the same on every machine,
# so they are the ones a staleness check may assert.
SOURCE_DERIVED = ["library", "interface", "api", "audit_coverage", "macros"]


def source_derived(current: dict) -> dict:
    return {section: current.get(section) for section in SOURCE_DERIVED}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true", help="write the baseline")
    parser.add_argument(
        "--check", action="store_true", help="exit non-zero if the baseline is stale"
    )
    parser.add_argument(
        "--acceptance",
        action="store_true",
        help="exit non-zero if the acceptance bar is violated",
    )
    args = parser.parse_args(argv)

    current = measure()
    rendered = json.dumps(current, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    # The bar is evaluated on its own, and it does not need the baseline to exist: a standard is
    # checked against the tree, not against a snapshot of the tree.
    if args.acceptance:
        report = check_acceptance(current)
        print(
            "THE ACCEPTANCE BAR - what the project must not lose, and where it is headed"
        )
        if report["violations"]:
            print(f"  {len(report['violations'])} VIOLATION(S):")
            for violation in report["violations"]:
                print(f"    violation: {violation}")
        else:
            print("  every constraint holds")
        print("  the constraints:")
        for entry in report["satisfied"]:
            print(f"    {entry}")
        print("  the targets - direction of travel, not gates:")
        for target in report["targets"]:
            print(f"    {target}")
        print(
            "  the deferred metrics - named with the command that would produce each:"
        )
        for entry in report["deferred"]:
            print(f"    {entry}")
        return 1 if report["violations"] else 0

    if args.write:
        MEASUREMENTS.write_text(rendered, encoding="utf-8")
        print(f"wrote {MEASUREMENTS.relative_to(REPO_ROOT)}")
        print_summary(current)
        return 0

    if not MEASUREMENTS.exists():
        print(
            f"missing {MEASUREMENTS.relative_to(REPO_ROOT)} - run `mise run audit:measure --write`"
        )
        return 1

    baseline = json.loads(MEASUREMENTS.read_text(encoding="utf-8"))
    before = flatten(baseline)
    after = flatten(current)

    print_summary(current)

    print("\nTHE DELTA - the baseline is committed, so a change is visible\n")
    changed = False
    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        if old == new:
            continue
        changed = True
        print(f"  {key}: {old} -> {new}")
    if not changed:
        print("  nothing moved")

    if not args.check:
        return 0

    # The staleness check asserts only the source-derived sections. The dependency section is
    # read from build artifacts, so it is not comparable on a machine that has never built -
    # and a check that fails where it cannot answer is worse than no check.
    stale = []
    old_source = flatten(source_derived(baseline))
    new_source = flatten(source_derived(current))
    for key in sorted(set(old_source) | set(new_source)):
        if old_source.get(key) != new_source.get(key):
            stale.append(f"{key}: {old_source.get(key)} -> {new_source.get(key)}")

    old_dependencies = baseline.get("dependencies", {})
    new_dependencies = current.get("dependencies", {})
    if old_dependencies.get("available") and new_dependencies.get("available"):
        if old_dependencies.get("reached_headers") != new_dependencies.get(
            "reached_headers"
        ):
            stale.append(
                "dependencies.reached_headers: "
                f"{old_dependencies.get('reached_headers')} -> "
                f"{new_dependencies.get('reached_headers')}"
            )
    elif old_dependencies.get("available") != new_dependencies.get("available"):
        print("\n  the dependency section is not comparable here (no build artifacts)")
    else:
        print("\n  the dependency section matched")

    if stale:
        print("\n  the baseline is stale:")
        for entry in stale:
            print(f"    {entry}")
        print("  run `mise run audit:measure --write` and commit the result")
        return 1
    print("\n  the baseline is up to date")
    return 0


def print_summary(current: dict) -> None:
    library = current["library"]
    interface = current["interface"]
    api = current["api"]
    coverage = current["audit_coverage"]
    dependencies = current["dependencies"]

    print("THE LIBRARY")
    print(f"  {library['files']} files, {library['code_lines']} lines of code")
    print(
        f"  the module interface is {library['module_interface_lines']} lines;"
        f" the hand-rolled formatter is {library['hand_rolled_formatter_lines']}"
        f" ({library['hand_rolled_formatter_share']:.0%} of the library)"
    )
    print(
        f"  the tests are {library['test_lines']} lines"
        f" ({library['test_to_library_ratio']:.2f} of the library)"
    )

    print("\nTHE INTERFACE DISCIPLINE")
    print(
        f"  standard-library includes in the module interface: "
        f"{interface['standard_library_includes']} (the rule is 0)"
    )
    print(
        f"  project includes in the module interface: "
        f"{', '.join(interface['project_includes']) or 'none'}"
    )

    print("\nTHE PUBLIC API")
    print(f"  {api['public_functions']} exported functions")
    if api["not_tested_at_source_level"]:
        print(
            f"  not called by the test file: {', '.join(api['not_tested_at_source_level'])}"
        )
    else:
        print("  every exported function is called by the test file")
    macros = current["macros"]
    print(f"  macros defined by the project: {len(macros['defined_by_the_project'])}")
    print(f"  macro invocations from Intel's `cib` package: {macros['cib_call_sites']}")

    print("\nTHE AUDIT'S OWN COVERAGE - where the research has actually been")
    print(f"  {coverage['library_source_lines']} library source lines in total")
    print(
        f"  {coverage['library_lines_cited_specifically']} cited with line numbers"
        f" ({coverage['specific_share']:.0%}) - read"
    )
    print(
        f"  {coverage['library_lines_cited_whole_file']} credited from a whole-file path"
        f" - looked at"
    )
    print(
        f"  {coverage['library_lines_seen']} seen in total ({coverage['seen_share']:.0%})"
    )
    uncited = []
    library_set = {str(path.relative_to(REPO_ROOT)) for path in library_files()}
    for relative, entry in sorted(coverage["per_file"].items()):
        if relative not in library_set:
            continue
        total = entry["source_lines"] or 1
        seen = min(
            entry["cited_lines"] + (total if entry["whole_file_cited"] else 0), total
        )
        if seen < total:
            uncited.append((relative, total - seen, total))
    for relative, missing, total in sorted(uncited, key=lambda item: -item[1])[:8]:
        print(f"    {relative:<45} {missing:4d} of {total:4d} lines unseen")
    never = sorted(library_set - set(coverage["per_file"]))
    for relative in never:
        print(f"    {relative:<45} never cited")

    # The read gap: the lines the audit has looked at - by naming the file - but not read at line
    # granularity. This is the list of where the next research goes, and it is sorted by size so
    # the biggest gap is first.
    gaps = []
    for relative, entry in sorted(coverage["per_file"].items()):
        if relative not in library_set:
            continue
        total = entry["source_lines"] or 1
        gap = total - entry["cited_lines"]
        if gap > 0:
            gaps.append((relative, gap, total))
    if gaps:
        print("    the read gap - looked at, but not read at line granularity:")
        for relative, gap, total in sorted(gaps, key=lambda item: -item[1]):
            print(f"      {relative:<45} {gap:4d} of {total:4d} lines")

    print("\nTHE DEPENDENCY CLOSURE")
    if dependencies.get("available"):
        print(f"  source: {dependencies['source']}")
        print(
            f"  {dependencies['installed_headers']} third-party headers are installed;"
            f" the project's compiled closure reaches {dependencies['reached_headers']}"
        )
        print(
            "  by package: "
            + ", ".join(
                f"{k} ({v})" for k, v in list(dependencies["packages"].items())[:8]
            )
        )
        reached = dependencies["reached_headers"]
        installed = dependencies["installed_headers"]
        if installed:
            print(
                f"  the closure reaches {reached / installed:.0%} of what is installed"
            )
        if dependencies.get("per_tree"):
            trees = dependencies["per_tree"]
            verdict = (
                "all agree" if dependencies.get("trees_agreeing") else "THEY DISAGREE"
            )
            print(
                f"  {len(trees)} build trees measured: {verdict}"
                f" ({', '.join(t['tree'] for t in trees)})"
            )
        fallback = dependencies.get("resolved_fallback")
        if fallback:
            gap = reached - fallback["reached_headers"]
            print(
                f"  the include-line resolver says {fallback['reached_headers']} headers"
                f" - {gap} fewer than the compiler's record"
            )
            print("    (it starts from the project's headers, so it misses what the")
            print(
                "     translation units pulled in; the compiler's number is the real one)"
            )
    else:
        print("  not measured: there is no populated install tree")

    print("\nWHAT THIS CANNOT MEASURE - it needs the build lane")
    for what, command in [
        ("coverage percentage", "cmake --workflow --preset gcc16-coverage"),
        ("the uncovered-line list", "gcov-16 --json-format, then the gate"),
        ("runtime cost per message", "the benchmark harness from part 18, section 4"),
        ("binary size", "a release build with size(1)"),
        ("sanitizer cleanliness", "cmake --workflow --preset gcc16-asan"),
    ]:
        print(f"  {what:<28} {command}")


if __name__ == "__main__":
    raise SystemExit(main())
