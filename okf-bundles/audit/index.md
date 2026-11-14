---
type: Audit Bundle
title: cpp-core C++26 Features Audit
description: Comprehensive audit of C++26 features, tooling, and compiler support
resource: https://github.com/ray-manaloto/cpp-core/tree/main/docs/cxx26-features-audit
tags:
  - audit
  - cxx26
  - cpp-core
  - features
  - compiler-support
  - tooling
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
  - features
  - compiler-support
  - tooling
sources:
  - id: source-code
    resource: https://github.com/ray-manaloto/cpp-core/tree/main/docs/cxx26-features-audit
    title: Original audit documentation
    author: human:ray-manaloto
    last_modified: 2026-11-14T00:00:00Z
---

## cpp-core C++26 Features Audit

Comprehensive audit of C++26 features, tooling, and compiler support for the cpp-core project.

## Overview

This bundle contains the complete C++26 features audit for the cpp-core project, documenting:

- Compiler support (GCC 16 + libstdc++, Clang p2996 + libc++)
- C++26 feature availability and migration paths
- Tooling design decisions
- Build system capabilities
- Audit verification system

## Audit Structure

| Document | Description | Parts |
|----------|-------------|-------|
| [open-items.md](open-items.md) | 70 open items + 19 answered + 1 contingent | Visual tracker |
| [decisions.md](decisions.md) | Full decision arguments | 14 decisions |
| [README.md](README.md) | Audit overview and structure | 1 |
| [log.md](log.md) | Update log | 1 |

## Audit Parts Index

| Part | Title | Type |
|------|-------|------|
| 1 | DEF (Defects) | 8 items |
| 2 | FMT (fmt/constexpr) | 13 items |
| 3 | QUIL (quill) | 7 items |
| 4 | TOOL (Tooling) | 13 items |
| 5 | MOD (import std;) | 11 items |
| 6 | REFL (Reflection) | 4 items |
| 7 | MAC (Macros) | 3 items |
| 8 | COV (Coverage) | 10 items |
| 9 | ENV (Environment) | 1 item |
| 10 | BUILD (Build) | 15 items |
| 11 | STEP (Plan Steps) | 10 items |
| 12 | VCPKG (vcpkg) | 5 items |
| 14 | DEF (Additional) | 1 item |
| 15 | PARKED (Lane Status) | 1 item |
| 16 | VERIF (Verification) | 1 item |
| 17 | ID-MAP (ID Mapping) | 1 item |
| 18 | STEP-DETAIL | 1 item |
| 19 | TOOL-DETAIL | 1 item |
| 20 | READ-GAP | 1 item |

## Audit Verification System

The audit includes a self-verification system (`scripts/verify_audit.py`) that checks:

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

## Audit Metrics

The audit measures:

- Project shape and discipline
- API surface area
- Audit coverage
- Dependency closure
- Automation value

Run metrics: `python3 scripts/audit_metrics.py`

## Upstream Verification

Vendored upstream copies are verified against `docs/cxx26-features-audit/upstream/manifest.json`

Run: `python3 scripts/verify_upstream.py`

## Related Bundles

| Bundle | Focus |
|--------|-------|
| [../architecture/](../architecture/) | System architecture documentation |
| [../../docs/asan-leak-check/](../../docs/asan-leak-check/) | ASAN leak investigation |
| [../../docs/module-source-location/](../../docs/module-source-location/) | Module source location research |

---

## Part of the cpp-core Audit Documentation Suite
