#!/usr/bin/env python3
"""The audit's citations: how they are written, and how to find them.

The audit cites the project's own code in three ways:

- a full path and a range: `modules/logging/format.hpp:220-281`
- a bare file name and a range: `format.hpp:284-294`
- a continuation of the citation before it: `, 270` or `` `:104-105` ``

and it mentions a file without a range at all:

- `format.hpp` is a private source

A citation into a header the audit quotes but does not own - `<format>:168-186`, or
`quill/Logger.h:427-433` - names a file of the toolchain's, and is not the subject of this
repository's audit. So is everything outside the citable set: the audit's own documents, the
vendored upstream copies, and the root README.

THE CONTEXT RULE. A shorthand continues the file named before it - on the same line, on a
later line of the same paragraph, or in the next row of the same table. A blank line or a
heading ends the context: a `:270` three paragraphs later is not a citation into whatever
was mentioned last.

A bare range after a comma (`format.hpp:239-241, 270`) is a citation only when it shares the
inline-code span with the file it continues. That is what keeps `2,048 bytes` - a number in
prose - from being read as two line numbers.

A citation is a claim about a range of lines. This module finds the claims; it does not judge
them. `anchor_citations.py` holds them still by hashing the lines they name.

Stdlib only. No compiler, no CMake, no network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "docs" / "cxx26-features-audit"

# The library's own code.
LIBRARY_GLOBS = [
    "modules/**/*.cppm",
    "modules/**/*.hpp",
    "include/**/*.hpp",
    "src/**/*.cpp",
    "tests/**/*.cpp",
]
# The build.
BUILD_GLOBS = [
    "CMakeLists.txt",
    "cmake/**/*.cmake",
    "cmake/**/*.json",
    "CMakePresets.json",
]
# The dependency contract: the manifest and the overlay ports.
DEPENDENCY_GLOBS = ["ports/**/*.cmake", "ports/**/*.json", "vcpkg.json"]

# The paths the audit is allowed to cite. The rest of the repository is not the subject.
CITABLE_PREFIXES = (
    "modules",
    "include",
    "src",
    "tests",
    "cmake",
    "ports",
    "CMakeLists.txt",
    "CMakePresets.json",
    "vcpkg.json",
)

# The file extensions a citation can name.
EXTENSIONS = "cppm|hpp|cpp|cmake|json|txt|h|md"

# A Markdown heading. `#include` is not one: the space is what makes the difference.
HEADING = re.compile(r"^#{1,6}\s+\S")

# One pass finds every citation form. The alternatives are ordered: a file with a range wins
# over a file without one, and a header reference breaks the context.
TOKEN = re.compile(
    r"(?P<header><[A-Za-z0-9_./+-]+>):(?P<hstart>\d+)(?:-(?P<hend>\d+))?"
    r"|(?P<path>[A-Za-z0-9_./-]+\.(?:" + EXTENSIONS + r"))"
    r"(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?"
    r"|(?P<tick>`):(?P<sstart>\d+)(?:-(?P<send>\d+))?"
    r"|(?P<comma>,)\s*(?P<bstart>\d+)(?:-(?P<bend>\d+))?"
)


@dataclass(frozen=True)
class Citation:
    """One claim about one range of lines."""

    document: str
    line: int
    file: str
    start: int
    end: int

    @property
    def lines(self) -> range:
        return range(self.start, self.end + 1)

    @property
    def where(self) -> str:
        return f"{self.document}:{self.line}"


def physical_lines(text: str) -> int:
    """The number of physical lines in a file's text.

    `text.split("\\n")` counts a trailing empty element, so a file of N lines that ends with a
    newline comes out as N + 1. The extra line does not exist, and crediting it inflates the
    denominator of the read-coverage share by one line per file.
    """
    if not text:
        return 0
    count = text.count("\n")
    if not text.endswith("\n"):
        count += 1
    return count


def source_lines(path: Path) -> list[str]:
    """The file's lines, without the phantom empty element a trailing newline leaves behind."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _glob(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(REPO_ROOT.glob(pattern))
    return sorted(set(files))


def library_files() -> list[Path]:
    """The library's own code."""
    return _glob(LIBRARY_GLOBS)


def build_files() -> list[Path]:
    """The build's own files."""
    return _glob(BUILD_GLOBS)


def dependency_files() -> list[Path]:
    """The dependency contract: the manifest and the overlay ports."""
    return _glob(DEPENDENCY_GLOBS)


def citable_files() -> list[Path]:
    """Every file the audit is allowed to cite."""
    return sorted(set(library_files() + build_files() + dependency_files()))


def _unique_by_name() -> dict[str, Path]:
    """The citable files whose name is unambiguous.

    `vcpkg.json` is not one of them: the root manifest and the three overlay manifests share
    the name. A bare name that could be two files resolves to neither, rather than to a guess.
    """
    grouped: dict[str, list[Path]] = {}
    for path in citable_files():
        grouped.setdefault(path.name, []).append(path)
    return {name: paths[0] for name, paths in grouped.items() if len(paths) == 1}


def resolve(raw: str) -> Path | None:
    """The file a citation names, or None when it names something the audit does not own.

    A full path is resolved against the repository root first: `vcpkg.json` is the root
    manifest, not one of the overlay manifests that share its name. A path that is only the
    tail of one - `toolchains/cpp-core.cmake` - is resolved by its tail, and only when that
    tail is unambiguous.
    """
    candidate = REPO_ROOT / raw
    if candidate.is_file():
        relative = str(candidate.relative_to(REPO_ROOT))
        return candidate if relative.startswith(CITABLE_PREFIXES) else None
    if "/" not in raw:
        return _unique_by_name().get(raw)
    suffix = "/" + raw
    tails = [
        path
        for path in citable_files()
        if str(path.relative_to(REPO_ROOT)).endswith(suffix)
    ]
    return tails[0] if len(tails) == 1 else None


def _code_spans(line: str) -> list[tuple[int, int]]:
    """The inline-code spans of a line, as the positions of their backticks."""
    spans: list[tuple[int, int]] = []
    index = 0
    while True:
        opening = line.find("`", index)
        if opening < 0:
            break
        closing = line.find("`", opening + 1)
        if closing < 0:
            break
        spans.append((opening, closing))
        index = closing + 1
    return spans


def _span_of(spans: list[tuple[int, int]], position: int) -> int | None:
    """The index of the code span a position is in, or None."""
    for index, (opening, closing) in enumerate(spans):
        if opening < position < closing:
            return index
    return None


def scan_document(text: str, document: str) -> tuple[list[Citation], set[str]]:
    """The citations a document makes, and the files it mentions without a range."""
    citations: list[Citation] = []
    mentions: set[str] = set()
    context: str | None = None
    in_fence = False

    for number, line in enumerate(text.split("\n"), 1):
        # A fenced code block is not prose, and a `#include` inside one is not a heading.
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        # A blank line or a heading ends the paragraph, and with it the context. The line
        # itself is still scanned: a citation can sit in a heading.
        if not line.strip() or (not in_fence and HEADING.match(line)):
            context = None

        spans = _code_spans(line)
        # The end of the last citation token, and the code span it was in. A bare range
        # continues that token, and only that token.
        previous_end: int | None = None
        previous_span: int | None = None

        for match in TOKEN.finditer(line):
            if match.group("header") is not None:
                # A header of the toolchain's: the context ends here.
                context = None
                previous_end = None
                continue

            raw = match.group("path")
            if raw is not None:
                path = resolve(raw)
                context = str(path.relative_to(REPO_ROOT)) if path else None
                start = match.group("start")
                if path is None or start is None:
                    # A mention of a file, not a citation of its lines.
                    if path is not None:
                        mentions.add(context or "")
                    previous_end = None
                    continue
                first = int(start)
                last = int(match.group("end") or first)
                citations.append(Citation(document, number, context or "", first, last))
                previous_end = match.end()
                previous_span = _span_of(spans, match.start())
                continue

            if match.group("tick") is not None:
                if context is not None:
                    first = int(match.group("sstart"))
                    last = int(match.group("send") or first)
                    citations.append(Citation(document, number, context, first, last))
                    previous_end = match.end()
                    previous_span = _span_of(spans, match.start() + 1)
                continue

            # A bare range after a comma: `format.hpp:239-241, 270`. It continues the
            # citation before it, and only when both are in the same inline-code span -
            # which is what keeps `2,048 bytes` from being read as two line numbers.
            if (
                context is not None
                and previous_end is not None
                and not line[previous_end : match.start()].strip()
            ):
                span = _span_of(spans, match.start())
                if span is not None and span == previous_span:
                    first = int(match.group("bstart"))
                    last = int(match.group("bend") or first)
                    citations.append(Citation(document, number, context, first, last))
                    previous_end = match.end()
                    previous_span = span
                    continue
            previous_end = None

    return citations, {name for name in mentions if name}


def all_citations() -> list[Citation]:
    """Every citation the audit makes."""
    found: list[Citation] = []
    for document in sorted(AUDIT_DIR.glob("*.md")):
        citations, _ = scan_document(
            document.read_text(encoding="utf-8"), document.name
        )
        found.extend(citations)
    return found


def audit_citations() -> tuple[dict[str, set[int]], set[str]]:
    """The source lines the audit has cited, and the files it cited only as a whole path.

    A file cited only as a path has been *looked at*; a file cited with line numbers has been
    *read*. The two are reported separately, because "the audit has seen every file" is a much
    weaker statement than "the audit has read every file".
    """
    cited: dict[str, set[int]] = {}
    whole_files: set[str] = set()
    for document in sorted(AUDIT_DIR.glob("*.md")):
        citations, mentions = scan_document(
            document.read_text(encoding="utf-8"), document.name
        )
        for citation in citations:
            cited.setdefault(citation.file, set()).update(citation.lines)
        whole_files |= mentions
    return cited, whole_files
