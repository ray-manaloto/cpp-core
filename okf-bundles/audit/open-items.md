---
type: Audit Document
title: Open Items — Canonical List
description: Canonical list of 70 open items + 19 answered + 1 contingent
resource: https://github.com/ray-manaloto/cpp-core/blob/main/docs/cxx26-features-audit/open-items.md
tags:
  - audit
  - open-items
  - cpp-core
  - tracking
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - audit
  - open-items
  - cpp-core
  - tracking
sources:
  - id: source-code
    resource: https://github.com/ray-manaloto/cpp-core/tree/main/docs/cxx26-features-audit
    title: Original audit documentation
    author: human:ray-manaloto
    last_modified: 2026-11-14T00:00:00Z
---

## Open Items — Canonical List

Canonical list of 70 open items + 19 answered + 1 contingent.

### Summary

| Status | Count |
|--------|-------|
| Open (need lane reopen) | 70 |
| Answered (decisions recorded) | 19 |
| Contingent (on BUILD-5) | 1 |

### Open Items by Category

#### DEF (Defects) — 8 items

| ID | Title | Status |
|----|-------|--------|
| DEF-1 | `set_level()` filters nothing on module path | 🔴 Open |
| DEF-2 | `{:f}` divergence — `%g` vs fixed | 🔴 Open |
| DEF-3 | Comments overstate standard (GMF "copied") | 🔴 Open |
| DEF-4 | Two paths disagree on format dialect | 🔴 Open |
| DEF-5 | Module never validates format spec vs type | 🔴 Open |
| DEF-6 | Catalog IDs renumber on every regeneration | 🔴 Open |
| DEF-7 | Catalog path level mapping inverted | 🔴 Open |
| DEF-8 | Formatter section header names wrong function | 🔴 Open |

#### FMT (fmt/constexpr) — 13 items

| ID | Title | Status | Blocked By |
|----|-------|--------|------------|
| FMT-1 | `FMT_STATIC_FORMAT` compile on both toolchains? | compile | Needs `FMT_USE_NONTYPE_TEMPLATE_ARGS` |
| FMT-2 | fmt compile-time formatting handle floating point? | compile | P3391R2 §2.4 says yes |
| FMT-3 | `FMT_STATIC_FORMAT` need constexpr `std::string`? | compile | Source says no — returns `char[N]` |
| FMT-4 | Can `format.hpp` be `constexpr` wholesale? | compile | 492-line formatter |
| FMT-5 | Does `static_assert` test pattern work? | compile | `format_message` const-eval with constexpr args |
| FMT-6 | What does fmt produce for project's float cases? | run | `%g` → shortest round-trip |
| FMT-7 | Does `format_to_n` truncate like `snprintf`? | compile | Error code must be checked |
| FMT-8 | Can custom `fmt::formatter<T>` interoperate with `fmtquill`? | compile | Two fmt copies |
| FMT-10 | `std::source_location::current()` in default arg returns caller's location? | compile | Same as MAC-1 |
| FMT-12 | Does `fmt::runtime` exist in 12.2.1 API? | compile | For `format_double` runtime spec |
| FMT-13 | Authoritative feature-test macro values on each toolchain? | compile | Part 21 worked example |
| FMT-14 | Module path format dialect: document, validate, or move? | 🟢 **DECIDED (c)** | Move formatting out; depends on QUIL-1 |
| FMT-15 | How to test 4 asymmetric compile-time divergences? | build-system | Need "must not compile" harness |

#### QUIL (quill) — 7 items

| ID | Question | Category | Notes |
|----|----------|----------|-------|
| QUIL-1 | Can a `Codec` push N fields from 1 pack element? | compile | **KEY BLOCKER** for FMT-14(c) |
| QUIL-2 | Which types push into `DynamicFormatArgStore` without formatter? | compile | `bool`, `char`, integers, float, double, `void*`, `string_view`, scoped enum? |
| QUIL-3 | Default-spec outputs: module `%g` vs fmt shortest round-trip? | run | Overlaps FMT-6 |
| QUIL-4 | Full spec cross-product: `#` with `b/x/o`, `0`+sign, `^`, precision on string? | compile + diff test | |
| QUIL-5 | Can `format_string` hold compile-time-rewritten template? | compile | `self_formatting` path needs this |
| QUIL-6 | Compiler accept non-terminated `char const[N]` at `consteval` boundary? | compile | `logging.cppm:67` — `safe_strnlen` OOB risk |
| QUIL-7 | >2047 byte message on `UnboundedBlocking` queue? | run | Would bounded queue throw `QuillError`? |
| QUIL-9 | 🟢 **DECIDED** — Document `flush()` caveat | 🟢 **DECIDED** | Static destructor hazard |

#### TOOL (Tooling) — 13 items

| ID | Question | Category | Priority |
|----|----------|----------|----------|
| TOOL-1 | `.clang-tidy` pass verify-config on Homebrew 23.1.5? | run | |
| TOOL-2 | Can clang-tidy parse `logging.cppm` standalone? | run | |
| TOOL-3 | Can Homebrew clang 23 BMI feed clang-tidy for `src/main.cpp`? | run | |
| TOOL-4 | Does clang-tidy on `src/app.cpp` parse cleanly with Homebrew clang 23? | run | |
| TOOL-5 | Exact on-disk layout after `cmake --build gcc16-coverage`? | run | |
| TOOL-6 | Does GCC 16 emit arcs for uninstantiated templates + `consteval` bodies? | run | **Decides if coverage numbers trustable** |
| TOOL-7 | Is `unexecuted_block` set on covered lines? strict vs line-only? | run | |
| TOOL-8 | Actual uncovered-line list today? (Confirm coverage-gaps.md) | run | |
| TOOL-9 | Does `ctest --preset gcc16-coverage` return non-zero on failure? | run | |
| TOOL-10 | Does catalog-generated file need explicit exclusion? | run | |
| TOOL-11 | Multi-TU line coverage: union vs sum? | run | |
| TOOL-12 | Branch coverage: `-b` usable? `-fcondition-coverage` stable? | run | Advisory only |
| TOOL-13 | 🟢 **DECIDED** — YAML + PyYAML via mise | 🟢 **DECIDED** | |
| TOOL-14 | 🟢 **DECIDED** — Accept cmake-format sweep | 🟢 **DECIDED** | |
| TOOL-15 | `.clang-format` + `.cmake-format` agree beyond `line_width=100`? | run | |

#### MOD (import std;) — 11 items

| ID | Question | Category | Notes |
|----|----------|----------|-------|
| MOD-1 | GCC migration size for option (c)? | compile | Which importer headers → `import std;`? |
| MOD-2 | Type-erasure boundary with fixed-size representation? | compile | Function pointer table / variant of primitives |
| MOD-3 | GCC 16 translate `#include` inside module unit? | compile | Diagnose [cpp.import]/2 ill-formedness? |
| MOD-4 | GCC 16 reject importer with only `<unistd.h>`? | compile | Isolated case untested |
| MOD-5 | Is `<unistd.h>` in GCC 16 importable-header set? | compile | [cpp.include]/10 translation |
| MOD-6 | Failure persist with `--compile-std-module`? | compile | Artefact of CMake not building header units? |
| MOD-7 | CMake dep scanning handle `#if` around `import std;`? | run | |
| MOD-8 | quill/cib/ut headers compile after `import std;` on p2996? | compile | libc++ documents include-after-import failures |
| MOD-9 | Catalog `nm` scan still find symbols with `import std;`? | run | |
| MOD-10 | TU importing module AND including `cib_quill.hpp` compile? | compile | No such TU today; test file imports + includes via ut |
| MOD-11 | 🟢 **Part 21 worked example** — GCC 16 matrix failure reproduce? | compile | Throwaway module + importer via `SOURCES_TYPE CXX_MODULE` |

#### REFL (Reflection) — 4 items

| ID | Question | Category |
|----|----------|----------|
| REFL-1 | clang-p2996 1-arg `members_of` vs GCC 2-arg — compile same source? | compile |
| REFL-2 | `access::unprivileged()` (P1306R5) vs `access_context::unchecked()` (P2996R13)? | compile |
| REFL-3 | `std::meta::exception` throwing in `consteval` — reliable? | compile |
| REFL-4 | When libstdc++/libc++ implement P3391R2, does `std::format_string<Args...>` accept project's format strings? | compile |

#### MAC (Macros) — 3 items

| ID | Question | Category | Related |
|----|----------|----------|---------|
| MAC-1 | `std::source_location::current()` in default arg → caller's location? | compile | = FMT-10 |
| MAC-2 | Catalog `nm` scan still find symbols if calls written macro-free? | run | = FMT-11 |
| MAC-3 | `std::format_string<Args...>` accept project's format strings? | compile | = REFL-4 |

#### COV (Coverage) — 10 items

| ID | Gap | Location |
|----|-----|----------|
| COV-1 | `trace`, `debug`, `critical` — never called by tests | `logging.cppm:85-151` |
| COV-2 | Level-filtering branches + message-below-threshold assertion | `quill_logger.cpp:105-119` |
| COV-3 | Almost every format spec: alignment, fill, sign, `#`, zero-pad, precision, `x/X/o/b`, uppercase, `^` | `format.hpp` |
| COV-4 | 2048-byte buffer truncation | `format.hpp:154-206` |
| COV-5 | `self_formatting` path — no such type exists | `format.hpp:424-463` |
| COV-6 | `is_array` and `string_like` branches | `format.hpp:70-72` |
| COV-7 | CIB/catalog path — `demo::run()` never called by tests | `src/app.cpp`, `cib_quill.hpp` |
| COV-8 | `quill_logger.cpp` internals: logger-creation races, `current_level` edge cases | `quill_logger.cpp` |
| COV-9 | `reflection_demo.cpp` runtime line only runs if called | `src/reflection_demo.cpp` |
| COV-10 | `log_raw` length path partially exercised | `logging.cppm:101-105` |

#### ENV (Environment) — 1 item

| ID | Item | Status |
|----|------|--------|
| ENV-1 | Two fmt copies — rule: custom formatters for `fmt` only | 🟢 **DECIDED** (structural) |
| ENV-2 | 🟢 **DECIDED** — Keep `build/coverage-clang/` + document | 🟢 **DECIDED** |
| ENV-3 | 🟢 **DECIDED** — Deferred (not a cpp-core decision) | 🟢 **DECIDED** |

### Items That Carry an ID and Are Answered or Contingent

The following items carry an ID and are answered or contingent (section 13 per the audit convention):

| ID | Title | Status |
|----|-------|--------|
| BUILD-5 | CI | Contingent |
| BUILD-7 | Where the stable catalog lives | Answered |
| BUILD-8 | Catalog message-set check | Answered |
| BUILD-8 | Feature-check gate | Answered |
| BUILD-9 | Feature-check gate | Answered |
| DEF-3 | Comments overstate standard | Answered |
| DEF-6 | Catalog IDs renumber | Answered |
| DEF-7 | Catalog path level mapping inverted | Answered |
| DEF-8 | Formatter section header names wrong | Answered |
| ENV-1 | Two fmt copies rule | Answered |
| ENV-2 | Keep coverage-clang build | Answered |
| ENV-3 | ZAI_API_KEY deferred | Answered |
| FMT-14 | Module path format dialect | Answered |
| QUIL-9 | Document flush() caveat | Answered |
| TOOL-13 | YAML + PyYAML via mise | Answered |
| TOOL-14 | Accept cmake-format sweep | Answered |

| Status | Count |
|--------|-------|
| Open (need lane reopen) | 70 |
| Answered (decisions recorded) | 19 |
| Contingent (on BUILD-5) | 1 |
