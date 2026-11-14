---
okf_version: "0.2"
title: cpp-core Architecture Documentation
description: Visual documentation suite for the cpp-core C++26 logging library
version: 1.0.0
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
---

Visual documentation suite for the cpp-core C++26 logging library.

## Contents

- [Component Diagram](./01-component-diagram.md) - High-level component architecture
- [Wire Protocol](./02-wire-protocol.md) - Sys-T wire format specification
- [Sequence Diagrams](./03-sequence-diagrams.md) - Runtime interaction sequences
- [Dependency Graph](./04-dependency-graph.md) - Module and library dependencies
- [Open Issues](./05-open-issues.md) - Known architectural concerns
- [Decision Log](./06-decision-log.md) - Architectural decisions and rationale

### Overview

This bundle contains the complete architecture documentation for cpp-core, a C++26 logging library built on top of Intel's compile-time-init-build (cib) framework and Quill logging backend.

The library implements two logging paths:

1. **Module path** - Import-based logging with compile-time format string validation
2. **Catalog path** - CIB macro-based logging with string catalog IDs

Both paths route through a standard-library-free interface to a Quill-backed implementation.
