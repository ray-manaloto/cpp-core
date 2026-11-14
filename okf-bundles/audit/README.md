---
type: Audit Document
title: C++26 Features Audit — README
description: Overview and structure of the C++26 features audit
resource: https://github.com/ray-manaloto/cpp-core/blob/main/docs/cxx26-features-audit/README.md
tags:
  - audit
  - cxx26
  - cpp-core
  - readme
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - audit
  - cxx26
  - cpp-core
  - readme
sources:
  - id: source-code
    resource: https://github.com/ray-manaloto/cpp-core/tree/main/docs/cxx26-features-audit
    title: Original audit documentation
    author: human:ray-manaloto
    last_modified: 2026-11-14T00:00:00Z
---

## C++26 Features Audit — README

Overview and structure of the C++26 features audit for the cpp-core project.

### Purpose

This audit documents the C++26 feature landscape relevant to the cpp-core project:

- Compiler support (GCC 16 + libstdc++, Clang p2996 + libc++)
- C++26 feature availability and migration paths
- Tooling design decisions
- Build system capabilities
- Audit verification system

### Audit Structure

The audit is organized into 21 parts, each in its own markdown file:

| Part | Title | Type | Status |
|------|-------|------|--------|
| 1 | DEF (Defects) | 8 items | Open |
| 2 | FMT (fmt/constexpr) | 13 items | Open |
| 3 | QUIL (quill) | 7 items | Open |
| 4 | TOOL (Tooling) | 13 items | Open |
| 5 | MOD (import std;) | 11 items | Open |
| 6 | REFL (Reflection) | 4 items | Open |
| 7 | MAC (Macros) | 3 items | Open |
| 8 | COV (Coverage) | 10 items | Open |
| 9 | ENV (Environment) | 1 item | Decided |
| 10 | BUILD (Build) | 15 items | Open |
| 11 | STEP (Plan Steps) | 10 items | Planned |
| 12 | VCPKG (vcpkg) | 5 items | Open |
| 14 | DEF (Additional) | 1 item | Open |
| 15 | PARKED (Lane Status) | 1 item | Decided |
| 16 | VERIF (Verification) | 1 item | Decided |
| 17 | ID-MAP (ID Mapping) | 1 item | Decided |
| 18 | STEP-DETAIL | 1 item | Planned |
| 19 | TOOL-DETAIL | 1 item | Planned |
| 20 | READ-GAP | 1 item | Decided |

### Audit Verification

The audit includes a self-verification system that checks:

- Item counts and consistency
- Duplicate and dangling IDs
- Decisions sheet against open items
- Prose counts against claims
- Markdown table shape and fence balance
- Relative links
- Parts tables agreement
- Privacy scan
- Vendored upstream copies
- Citation anchoring

Run verification: `python3 scripts/verify_audit.py`

### Audit Metrics

The audit measures:

- Project shape and discipline
- API surface area
- Audit coverage
- Dependency closure
- Automation value

Run metrics: `python3 scripts/audit_metrics.py`

### Upstream Verification

Vendored upstream copies are verified against `upstream/manifest.json`

Run: `python3 scripts/verify_upstream.py`

### Build Lane Status

**The build lane is parked.** As of 2026-11-12, the owner's decision is that this repository is research-only:

- No builds, no compiler or toolchain installs or configuration
- No CMake or preset runs
- No test, sanitizer or coverage runs
- Source files are out of scope — the documentation is in scope
- Anything that would need a compile is written down as an open item instead of guessed at

### Related Documentation

| Bundle | Focus |
|--------|-------|
| [../../okf-bundles/architecture/](../../okf-bundles/architecture/) | System architecture documentation |
| [../../docs/asan-leak-check/README.md](../../docs/asan-leak-check/README.md) | ASAN leak investigation |
| [../../docs/module-source-location/README.md](../../docs/module-source-location/README.md) | Module source location research |
