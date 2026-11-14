---
type: Project Document
title: PARKED — Work Status Map
description: Where the cpp-core work stands so it can be picked up without re-deriving anything
resource: https://github.com/ray-manaloto/cpp-core
tags:
  - cpp-core
  - parked
  - work-status
  - research
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - cpp-core
  - parked
  - work-status
  - research
sources:
  - id: audit-bundle
    resource: ./okf-bundles/audit/index.md
    title: C++26 features audit bundle
  - id: architecture-bundle
    resource: ./okf-bundles/architecture/index.md
    title: Architecture documentation bundle
  - id: asan-leak-check
    resource: ./docs/asan-leak-check/README.md
    title: ASAN leak-check documentation
  - id: module-source-location
    resource: ./docs/module-source-location/README.md
    title: Module source location research
---

## PARKED — Work Status Map

> **This is a pointer document.** The full parked work documentation has been migrated to OKF bundles.
> See the linked bundles below for complete documentation.

### Status

**The build lane is parked.** As of 2026-11-12 the owner's decision is that this repository is research-only:

- No builds, no compiler or toolchain installs or configuration, no CMake or preset build runs, no test, sanitizer or coverage runs
- **Source files are out of scope** — the documentation is in scope
- Anything that would need a compile is written down as an open item instead of guessed at

`PARKED.md` records what is parked and what the plan is when the lane reopens. Do not "just try it" with a compiler.

### Research Complete — Documentation Migrated to OKF Bundles

The research for all three parts of the original request is complete and documented in OKF bundles:

| Original Request Part | Documentation |
|----------------------|---------------|
| 1. C++26 / third-party-library features that replace hand-rolled code | [Audit Bundle](./okf-bundles/audit/index.md) — 21-part audit |
| 2. clang-format, clang-tidy, cmake-format and 100% unit-test coverage | [Architecture Bundle](./okf-bundles/architecture/index.md) + [Audit Bundle → Tooling](./okf-bundles/audit/open-items.md#tool-tooling--13-items) |
| 3. Macros reduced/eliminated in favor of C++26 features | [Audit Bundle → Macro Reduction](./okf-bundles/audit/macro-reduction.md) + [Architecture Bundle](./okf-bundles/architecture/index.md) |

### Key Decisions (All 14 Answered)

See [Audit Bundle → Decisions](./okf-bundles/audit/decisions.md) for full rationale.

| # | Decision | Answer |
|---|----------|--------|
| **FMT-14** | Module path format dialect | **(c) use fmtlib** — single formatter for both paths; depends on QUIL-1 |
| **TOOL-13** | `.cmake-format.yaml` or `.cmake-format.json` | **YAML** — add PyYAML via mise |
| **TOOL-14** | One-shot `cmake-format -i` sweep? | **Accept the sweep** — 9 of 12 files change; review diff |
| **BUILD-7** | Where the stable catalog lives | **(a) Use CIB's stable ID mechanism** per logging.adoc / binary_stable_ids |
| **BUILD-1** | Warning flags | **All at once**: `-Wall -Wextra -Wpedantic -Wconversion -Wshadow` |
| **BUILD-2** | Consumability | **Add install/export now** for current shape |
| **BUILD-3** | Public header surface | **All three PRIVATE**, only module is public |
| **BUILD-4** | `clang23` | **Conditional**: add preset + triplet when Homebrew libc++ has `<meta>` |
| **BUILD-5** | CI | **No CI yet**, local presets |
| **BUILD-8** | Catalog message-set check | **Yes**, part of coverage work |
| **BUILD-8** | Feature-check gate | **(c) Check only where answer gates code path** |
| **QUIL-9** | `flush()` caveat | **Document in both** module header + README |
| **ENV-2** | Abandoned tree | **Keep + document** with README |
| **ENV-3** | `ZAI_API_KEY` | **Deferred**, not a cpp-core decision |

### What's Done and Committed

- ASan leak check on `p2996-asan`: `fd79fc0`, `87d2fcf`
- Macro-free source location in the module: `8800b0a`
- clang-format configuration: `61ba2da`
- `.editorconfig` made to agree with formatter: `2ef42de`
- Features audit in 21 parts: [Audit Bundle](./okf-bundles/audit/index.md)
- SDLC subagent role definitions: `22b6a65`

### Research Complete — All in OKF Bundles

#### Architecture Documentation (7 visual documents)

[Architecture Bundle](./okf-bundles/architecture/index.md):

- Component Diagram — system components, data flow, boundaries
- Wire Protocol — Quill vs Catalog-typed wire format comparison
- Sequence Diagrams — detailed runtime interaction sequences
- Dependency Graph — all external dependencies with versions
- Open Issues — visual tracker for 70 open items
- Decision Log — all 14 architectural decisions with rationale
- Architecture README — bundle overview

#### C++26 Features Audit (21 parts)

[Audit Bundle](./okf-bundles/audit/index.md):

- 70 open items + 19 answered + 1 contingent
- 14 decisions with full rationale
- Verification system (`scripts/verify_audit.py`)
- Metrics harness (`scripts/measure.py`)
- Upstream verification (`scripts/verify_upstream.py`)

#### Other Research

- ASAN leak-check analysis: [docs/asan-leak-check/README.md](./docs/asan-leak-check/README.md)
- Module source location research: [docs/module-source-location/README.md](./docs/module-source-location/README.md)

### The Three-Part Request — Research Complete

1. **C++26 / third-party-library features that replace hand-rolled code** → [Audit Bundle](./okf-bundles/audit/index.md)
2. **clang-format, clang-tidy, cmake-format and 100% unit-test coverage set up** → [Architecture Bundle](./okf-bundles/architecture/index.md) + [Audit Bundle → Tooling](./okf-bundles/audit/open-items.md#tool-tooling--13-items)
3. **Macros reduced or eliminated in favour of C++26 features, static reflection and templates** → [Audit Bundle → Macro Reduction](./okf-bundles/audit/macro-reduction.md)

### The Research Lane — Complete

The research for all three parts is complete and written down. What remains is the implementation, which is parked.

### Not Started — Next Steps When Lane Reopens

When the build lane reopens, see [Audit Bundle → Decisions](./okf-bundles/audit/decisions.md#first-10-steps-when-lane-reopens) for the ordered plan:

1. Fix the level-filtering defect (DEF-1) + test
2. Add `"fmt"` to `vcpkg.json` (already installed, manifest change only)
3. Mark `format.hpp` functions `constexpr` (15 functions)
4. Add `static_assert` formatter tests
5. Replace `snprintf` with fmt in `format_double`
6. Use `fmt::format` for cib tag string
7. Move formatting out of module interface (depends on QUIL-1)
8. Wire formatting into CMake
9. Coverage gate at 100%
10. `import std;` decision — keep status quo

### Open Items Summary

| Status | Count |
|--------|-------|
| Open (need lane reopen) | 70 |
| Answered (decisions recorded) | 19 |
| Contingent (on BUILD-5) | 1 |

See [Audit Bundle → Open Items](./okf-bundles/audit/open-items.md) for the canonical list.

### Key Defects Still Open

| ID | Title |
|----|-------|
| DEF-1 | `set_level()` filters nothing on module path |
| DEF-2 | `{:f}` divergence — `%g` vs fixed |
| DEF-3 | Comments overstate standard (GMF "copied") |
| DEF-4 | Two paths disagree on format dialect |
| DEF-5 | Module never validates format spec vs type |
| DEF-6 | Catalog IDs renumber on every regeneration |
| DEF-7 | Catalog path level mapping inverted at both ends |
| DEF-8 | Formatter section header names wrong function |

See [Audit Bundle → Open Items](./okf-bundles/audit/open-items.md) for all 70 items.

### Key Research Findings

1. **Use fmt, not `std::format`** — fmt's compile-time API includes floating point; `std::format` excludes floats from constant evaluation. Neither libstdc++ 16 nor libc++ 21 implements `constexpr std::format`.

2. **Make everything `constexpr` / `consteval` wherever possible** — 15 functions in `format.hpp` can be `constexpr`; turns formatting rules into `static_assert` compiler checks.

3. **`import std;` works on both toolchains** but removes the standard-library-free constraint only on clang-p2996. On GCC 16 every importing TU would have to stop including standard headers.

4. **Static reflection cannot replace anything today** — every `std::meta` range-returning metafunction allocates; neither compiler implements constexpr allocation.

5. **Intel's `stdx` cannot enter the module interface** — it includes standard headers and fmt.

6. **The CIB macros stay** — each macro has a macro-free equivalent but costs verbosity.

7. **The `set_level()` defect (DEF-1)** — level filtering doesn't work on module path; three-line fix in two call sites.

8. **QUIL-1 is the key blocker** — Can a `quill::Codec` push N fields from one pack element? Required for FMT-14(c).

### All Documentation in OKF Bundles

| Bundle | Path | Documents |
|--------|------|-----------|
| Architecture | `./okf-bundles/architecture/` | 7 documents |
| Audit | `./okf-bundles/audit/` | 5+ documents |
| ASAN Leak Check | `./docs/asan-leak-check/README.md` | 1 document |
| Module Source Location | `./docs/module-source-location/README.md` | 1 document |

### When Lane Reopens

See [Audit Bundle → Decisions → First 10 Steps](./okf-bundles/audit/decisions.md#first-10-steps-when-lane-reopens) for the exact ordered plan.

**Do not "just try it" with a compiler.** The lane is parked for a reason — the research is complete, the implementation is not.
