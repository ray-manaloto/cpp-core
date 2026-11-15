---
type: Project Document
title: cpp-core — C++26 Logging Library
description: A small C++26 library: a logging module (`com.rsm.logging`), a string-catalog path, and C++26 static reflection
resource: https://github.com/ray-manaloto/cpp-core
tags:
  - cpp-core
  - cpp26
  - logging
  - module
  - cib
  - quill
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - cpp-core
  - cpp26
  - logging
  - module
  - cib
  - quill
sources:
  - id: architecture-bundle
    resource: ./okf-bundles/architecture/index.md
    title: Architecture documentation bundle
  - id: audit-bundle
    resource: ./okf-bundles/audit/index.md
    title: C++26 features audit bundle
  - id: asan-leak-check
    resource: ./docs/asan-leak-check/README.md
    title: ASAN leak-check documentation
  - id: module-source-location
    resource: ./docs/module-source-location/README.md
    title: Module source location research
---

## cpp-core

A small C++26 library: a logging module (`com.rsm.logging`), a string-catalog path, and C++26
static reflection. It builds with two compilers, GCC 16 (libstdc++) and clang-p2996 (libc++),
and it is deliberately conservative about what enters the module interface.

> **This is a pointer document.** The full documentation has been migrated to OKF bundles.
> See the linked bundles below for complete documentation.

### Quick Links

| Topic | Documentation |
|-------|---------------|
| **Architecture** | [Architecture Bundle](./okf-bundles/architecture/index.md) — 7 visual documents with Mermaid diagrams |
| **C++26 Features Audit** | [Audit Bundle](./okf-bundles/audit/index.md) — 21-part audit with 70 open items |
| **ASAN Leak Check** | [ASAN Leak Check](./docs/asan-leak-check/README.md) |
| **Module Source Location** | [Module Source Location](./docs/module-source-location/README.md) |
| **Build & Test** | See [Build](#build) section below |
| **Logging** | See [Architecture Bundle → Component Diagram](./okf-bundles/architecture/01-component-diagram.md#component-responsibilities) |

### Layout

| Path | What it is |
|------|------------|
| `modules/logging/` | The `com.rsm.logging` module: the logging library's public interface. |
| `include/cpp-core/logging/` | The headers that the module's implementation and the cib path share. |
| `src/` | The application: the CIB demo (`app.cpp`), the reflection demo (`reflection_demo.cpp`) and the quill logger (`logging/quill_logger.cpp`). |
| `tests/` | The tests, written with [ut](https://github.com/stephenberry/ut). |
| `cmake/` | The toolchain, the presets, the catalog and the include-what-you-use integration. |
| `ports/` | The vcpkg overlay ports. |
| `docs/` | The research: the [C++26 and third-party features audit](okf-bundles/audit/index.md), the ASan leak-check analysis and the module source-location study. |
| `scripts/` | The checks that do not need a compiler: `mise run audit:verify` runs them all, `mise run audit:measure` measures the project. |

### Build

```sh
cmake --workflow --preset gcc16-release    # configure + build + test
cmake --workflow --preset p2996-debug
cmake --list-presets                       # all presets
```

| Compiler | debug | release | asan | tsan | iwyu |
|---|---|---|---|---|---|
| GCC 16.2 (`-freflection`) | `gcc16-debug` | `gcc16-release` | `gcc16-asan` | none on macOS | none |
| clang-p2996 (libc++, reflection) | `p2996-debug` | `p2996-release` | `p2996-asan` | `p2996-tsan` | `p2996-iwyu` |

See [Architecture Bundle → Dependency Graph](./okf-bundles/architecture/04-dependency-graph.md) for full dependency graph and version matrix.

### Logging

Two logging paths share one quill logger: the **module path** and the **catalog path**.

See [Architecture Bundle → Component Diagram](./okf-bundles/architecture/01-component-diagram.md) for full details.

#### Module Path

```cpp
import com.rsm.logging;
com::rsm::logging::info("The answer is {}", 42);
```

#### Catalog Path

```cpp
#include <cpp-core/logging/cib_quill.hpp>

namespace my_module {
CIB_LOG_MODULE("my_module");
auto f() {
  CIB_INFO("The answer is: {}", 42);          // compile-time arg folded into format string
  CIB_INFO("point has {} data members", count); // runtime arg interpolated by quill
}
}
```

See [Architecture Bundle → Wire Protocol](./okf-bundles/architecture/02-wire-protocol.md) for wire format comparison.

### Tests

The tests use [ut](https://github.com/stephenberry/ut):

```cpp
import com.rsm.logging;
#include "ut/ut.hpp"
using namespace ut;

suite tests = [] {
  "the level can be set and read back"_test = [] {
    com::rsm::logging::set_level(com::rsm::logging::level::warning);
    expect(com::rsm::logging::current_level() == com::rsm::logging::level::warning);
  };
};
```

### Key Rules

- **Both compilers keep working.** `gcc16` (GCC 16.2, libstdc++) and `p2996` (clang-p2996, libc++), both in C++26 mode.
- **The module interface stays free of the C++ standard library.** (See [Architecture Bundle → Component Diagram](./okf-bundles/architecture/01-component-diagram.md#boundary-rules-enforced))
- **`modules/logging/format.hpp` is private.** It is the module's own formatter; it is not in the public interface.
- **The vcpkg manifest and the overlay ports are the dependency contract.** The manifest is `vcpkg.json`; the overlays are in `ports/`; the triplet is in `triplets/`.
- **The catalog IDs are wire identifiers.** They are the `ID` attributes a MIPI Sys-T consumer decodes against.
- **Custom formatters are written for `fmt` only** — quill bundles its own copy of fmt (`fmtquill`), and the two copies are structural.
- **The test framework's module variant is not used.** `import ut;` makes the `std` module reachable in the test translation unit and GCC 16 then collides with the standard headers the test file needs.

### Privacy

- No machine name, host name, LAN address, tailnet name, account name, organisation name, real name or private project name is ever written into a tracked file.
- This is forward-only — old branches, worktrees, commits, closed pull requests and old job logs are **not** scrubbed.
- No key value is ever printed. Report key-file paths only.
- Values are injected with `mise run secret:set NAME` - the value is piped in, never passed as an argument. `secret:set` is a task in the user's global mise config, not in this repository; a clone without that global config does not have it.

### Full Documentation

See the OKF bundles for complete documentation:

| Bundle | Description |
|--------|-------------|
| [Architecture](./okf-bundles/architecture/index.md) | 7 visual documents with Mermaid diagrams (components, wire protocol, sequences, dependencies, open issues, decisions) |
| [Audit](./okf-bundles/audit/index.md) | 21-part C++26 features audit (70 open items, 19 decisions, verification system) |
| [ASAN Leak Check](./docs/asan-leak-check/README.md) | ASAN leak-check analysis |
| [Module Source Location](./docs/module-source-location/README.md) | Module source location research |

### Agent Skills

- `implement` - build one ticket from an existing plan, staged, not committed.
- `implement-spec` - build every open ticket of a spec, one worker per ticket.
- `work` - set the repository up, then name the next ready ticket.
- `visual-plan` - publish a plan as a commentable page.
- `ticket-retro` - the retrospective when a ticket or spec is finished.
