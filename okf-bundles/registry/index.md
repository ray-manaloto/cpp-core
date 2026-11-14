---
okf_version: "0.2"
title: cpp-core Offline Documentation Registry
description: Master registry of all OKF bundles - offline documentation repositories maintained for the cpp-core project
version: 1.0.0
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - cpp-core
  - registry
  - okf-bundles
  - offline-docs
  - documentation-index
sources:
  - id: architecture-bundle
    resource: ./architecture/index.md
    title: Architecture Documentation Bundle
  - id: audit-bundle
    resource: ./audit/index.md
    title: C++26 Features Audit Bundle
  - id: hk-builtins-bundle
    resource: ./hk-builtins/index.md
    title: hk Builtins Offline Documentation
  - id: asan-leak-check
    resource: ./asan-leak-check/index.md
    title: ASAN Leak Check Documentation
  - id: module-source-location
    resource: ./module-source-location/index.md
    title: Module Source Location Research
  - id: project-meta
    resource: ./project-meta/index.md
    title: Project Metadata and Configuration
---

## cpp-core Offline Documentation Registry

Master registry of all OKF bundles maintained for the cpp-core project. Each bundle is a self-contained offline documentation repository with its own index, log, and source tracking.

### Bundle Inventory

| Bundle | Path | Documents | Source | Last Updated |
|--------|------|-----------|--------|--------------|
| **Architecture** | `./architecture/` | 7 | Original research + Mermaid diagrams | 2026-11-14 |
| **Audit** | `./audit/` | 6 | C++26 features audit (21 parts) | 2026-11-14 |
| **hk-builtins** | `./hk-builtins/` | 4 | hk.jdx.dev/builtins.html (v2.12.0) | 2026-11-14 |
| **ASAN Leak Check** | `./asan-leak-check/` | 1 | Original research | 2026-11-14 |
| **Module Source Location** | `./module-source-location/` | 1 | Original research | 2026-11-14 |
| **Project Meta** | `./project-meta/` | 1 | Project configuration | 2026-11-14 |

## Total: 6 bundles, 24 documents

### Bundle Details

#### 1. Architecture Bundle

**Path**: `./architecture/`
**Index**: `./architecture/index.md`
**Log**: `./architecture/log.md`
**Documents**:

- `01-component-diagram.md` - High-level component architecture with Mermaid
- `02-wire-protocol.md` - Sys-T wire format specification
- `03-sequence-diagrams.md` - Runtime interaction sequences
- `04-dependency-graph.md` - Module and library dependencies with versions
- `05-open-issues.md` - Known architectural concerns (70 items)
- `06-decision-log.md` - Architectural decisions and rationale (14 decisions)
- `07-architecture-readme.md` - Bundle overview

#### 2. Audit Bundle

**Path**: `./audit/`
**Index**: `./audit/index.md`
**Log**: `./audit/log.md`
**Documents**:

- `open-items.md` - Canonical list of 70 open items + 19 answered + 1 contingent
- `decisions.md` - Full decision arguments for 14 decisions
- `README.md` - Audit overview and structure
- `macro-reduction.md` - Can C++26 features replace macros?
- `reflection.md` - C++26 static reflection (P2996) against the C++26 text
- `log.md` - Update log

#### 3. hk-builtins Bundle

**Path**: `./hk-builtins/`
**Index**: `./hk-builtins/index.md`
**Log**: `./hk-builtins/log.md`
**Documents**:

- `lychee.md` - Fast, async, stream-based link checker
- `lychee-extended.md` - Flint's repository-aware link check
- `index.md` - Bundle overview and quick reference
- `log.md` - Update log

**Source**: [hk.jdx.dev/builtins.html](https://hk.jdx.dev/builtins.html) (v2.12.0, 2026-11-09)

#### 4. ASAN Leak Check

**Path**: `./asan-leak-check/`
**Index**: `./asan-leak-check/index.md`
**Log**: `./asan-leak-check/log.md`
**Documents**:

- `index.md` - Full analysis summary with findings, solutions, verification
- `log.md` - Update log

#### 5. Module Source Location

**Path**: `./module-source-location/`
**Index**: `./module-source-location/index.md`
**Log**: `./module-source-location/log.md`
**Documents**:

- `index.md` - Research summary with technique, implementation, verification
- `log.md` - Update log

#### 6. Project Meta

**Path**: `./project-meta/`
**Index**: `./project-meta/index.md`
**Log**: `./project-meta/log.md`
**Documents**:

- `index.md` - Tool versions, config files, hk summary, CMake presets, vcpkg deps
- `log.md` - Update log

### Usage

#### View All Bundles

```sh
ls okf-bundles/
```

#### View Specific Bundle

```sh
cat okf-bundles/architecture/index.md
cat okf-bundles/audit/index.md
cat okf-bundles/hk-builtins/index.md
```

#### Cross-Reference

All bundles reference each other via relative paths:

- Architecture ↔ Audit (open issues, decisions)
- hk-builtins is standalone (external tool docs)
- ASAN, Module Source Location, Project Meta are standalone research docs

### Maintenance

#### Adding a New Bundle

1. Create directory under `okf-bundles/<name>/`
2. Add `index.md` with OKF frontmatter
3. Add `log.md` with creation entry
4. Add document files
5. Update this registry (`registry/index.md`)

#### Updating a Bundle

1. Update documents in bundle directory
2. Update bundle's `log.md`
3. Update bundle's `index.md` if structure changes
4. Update this registry's "Last Updated" column

#### Source Tracking

Each bundle's `index.md` includes a `sources` section tracking:

- Original source URL
- Author
- Last modified date
- Local copy location

### Related

- [Architecture Bundle](../architecture/index.md)
- [Audit Bundle](../audit/index.md)
- [hk-builtins Bundle](../hk-builtins/index.md)
- [Project Root AGENTS.md](../../AGENTS.md)
- [Project Root PARKED.md](../../PARKED.md)
- [Project Root README.md](../../README.md)
