---
type: Architecture Document
title: Architecture Documentation — cpp-core
description: Visual documentation suite for the cpp-core C++26 logging library
resource: https://github.com/ray-manaloto/cpp-core/blob/main/docs/architecture/README.md
tags:
  - architecture
  - cpp-core
  - cpp26
  - logging
  - visualization
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - architecture
  - cpp-core
  - cpp26
  - logging
  - visualization
sources:
  - id: source-code
    resource: https://github.com/ray-manaloto/cpp-core/tree/main/docs/architecture
    title: Original architecture documentation
    author: human:ray-manaloto
    last_modified: 2026-11-14T00:00:00Z
---

## Architecture Documentation — cpp-core

Visual documentation suite for the cpp-core C++26 logging library.

### Overview

This bundle contains the complete architecture documentation for cpp-core, a C++26 logging library built on top of Intel's compile-time-init-build (cib) framework and Quill logging backend.

The library implements two logging paths:

1. **Module path** - Import-based logging with compile-time format string validation
2. **Catalog path** - CIB macro-based logging with string catalog IDs

Both paths route through a standard-library-free interface to a Quill-backed implementation.

### Documentation Suite

| Document | Description | Status |
|----------|-------------|--------|
| [01-component-diagram.md](01-component-diagram.md) | System components, modules, data flow, and boundaries | ✅ Complete |
| [02-wire-protocol.md](02-wire-protocol.md) | Quill vs Catalog-typed wire protocol comparison | ✅ Complete |
| [03-sequence-diagrams.md](03-sequence-diagrams.md) | Detailed runtime interaction sequences | ✅ Complete |
| [04-dependency-graph.md](04-dependency-graph.md) | All external dependencies with versions | ✅ Complete |
| [05-open-issues.md](05-open-issues.md) | Visual tracker for 70 open items | ✅ Complete |
| [06-decision-log.md](06-decision-log.md) | All 14 architectural decisions with rationale | ✅ Complete |
| [07-architecture-readme.md](07-architecture-readme.md) | This file — bundle overview | ✅ Complete |

### Visual Theme

All diagrams use a consistent Modern Minimalist theme:

- Primary: `#36454f` (Graphite)
- Secondary: `#708090` (Slate)
- Background: `#ffffff` (White)
- Text: `#36454f` (Graphite)

### Quick Reference

| Document | Focus | Key Diagrams |
|----------|-------|--------------|
| 01-component-diagram.md | System components, data flow, boundaries | Component, Sequence, Class, Boundary |
| 02-wire-protocol.md | Quill vs Catalog-typed wire format | Record structure, Header comparison, Delta |
| 03-sequence-diagrams.md | Runtime interaction sequences | Module path, Catalog path, Init, Flush, Level change |
| 04-dependency-graph.md | External dependencies with versions | Dependency tree, Build graph, Version matrix |
| 05-open-issues.md | 70 open items visual tracker | Pie charts, dependency graph, progress |
| 06-decision-log.md | All 14 architectural decisions | Decision matrix, dependency graph |

### Bundle Structure

```text
architecture/
├── index.md                    # This file
├── 01-component-diagram.md    # System components & data flow
├── 02-wire-protocol.md        # Quill vs Catalog-typed wire protocol
├── 03-sequence-diagrams.md    # Runtime interaction sequences
├── 04-dependency-graph.md     # External dependencies with versions
├── 05-open-issues.md          # Visual tracker for 70 open items
├── 06-decision-log.md         # All 14 architectural decisions
└── 07-architecture-readme.md  # This file
```

### Diagram Standards

All Mermaid diagrams use consistent theme:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#36454f',
    'secondaryColor': '#708090',
    'background': '#ffffff',
    'textColor': '#36454f',
    'edgeLabelBackground': '#f0f0f0'
  }
}}%%
```

Color palette:

- Primary: `#36454f` (Graphite)
- Secondary: `#708090` (Slate)
- Background: `#ffffff` (White)
- Text: `#36454f` (Graphite)

### Theme: Modern Minimalist

Generated: 2026-11-14

### Quick Navigation

| Document | Focus | Key Diagrams |
|----------|-------|--------------|
| [01-component-diagram.md](01-component-diagram.md) | System components, data flow, boundaries | Component, Sequence, Class, Boundary |
| [02-wire-protocol.md](02-wire-protocol.md) | Quill vs Catalog-typed wire protocol | Record structure, Header comparison, Delta |
| [03-sequence-diagrams.md](03-sequence-diagrams.md) | Runtime interaction sequences | Module path, Catalog path, Init, Flush, Level change |
| [04-dependency-graph.md](04-dependency-graph.md) | External dependencies with versions | Dependency tree, Build graph, Version matrix |
| [05-open-issues.md](05-open-issues.md) | Visual tracker for 70 open items | Pie charts, dependency graph, progress |
| [06-decision-log.md](06-decision-log.md) | All 14 architectural decisions | Decision matrix, dependency graph |

### Related Documentation

| Bundle | Focus |
|--------|-------|
| [../audit/](../audit/) | C++26 features audit (21 parts) |
| [../asan-leak-check/](../asan-leak-check/) | ASAN leak investigation |
| [../module-source-location/](../module-source-location/) | Module source location research |
| [../project-meta/](../project-meta/) | Project metadata and configuration |

---

## Part of the cpp-core Architecture Documentation Suite
