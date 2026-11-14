---
type: Audit Document
title: Decisions — Full Arguments
description: Full decision arguments for all 14 architectural decisions
resource: https://github.com/ray-manaloto/cpp-core/blob/main/docs/cxx26-features-audit/decisions.md
tags:
  - audit
  - decisions
  - cpp-core
  - rationale
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - audit
  - decisions
  - cpp-core
  - rationale
sources:
  - id: source-code
    resource: https://github.com/ray-manaloto/cpp-core/tree/main/docs/cxx26-features-audit
    title: Original audit documentation
    author: human:ray-manaloto
    last_modified: 2026-11-14T00:00:00Z
---

## Decisions — Full Arguments

Full decision arguments for all 14 architectural decisions.

### Decision Index

| # | ID | Title | Status | Date | Impact |
|---|----|-------|--------|------|--------|
| 1 | DEF-3 | Comments overstate standard (GMF "copied") | 🔴 Open | 2026-11-14 | Comment-only fix |
| 2 | DEF-6 | Catalog IDs renumber on regeneration | 🔴 Open | BUILD-7 | Wire format stability |
| 3 | DEF-7 | Catalog path level mapping inverted | 🔴 Open | 2026-11-14 | Level mapping table |
| 4 | DEF-8 | Formatter section header names wrong | 🔴 Open | 2026-11-14 | Comment-only |
| 5 | FMT-14 | Module path format dialect | 🟢 **DECIDED (c)** | 2026-11-14 | Move formatting out |
| 6 | QUIL-9 | Document `flush()` caveat | 🟢 **DECIDED** | 2026-11-14 | Header + README |
| 7 | TOOL-13 | YAML + PyYAML via mise | 🟢 **DECIDED** | 2026-11-14 | mise config |
| 8 | TOOL-14 | Accept cmake-format sweep | 🟢 **DECIDED** | 2026-11-14 | cmake-format |
| 9 | ENV-1 | Two fmt copies rule | 🟢 **DECIDED** | 2026-11-14 | Structural |
| 10 | ENV-2 | Keep coverage-clang build + document | 🟢 **DECIDED** | 2026-11-14 | Documentation |
| 11 | ENV-3 | Deferred (not cpp-core decision) | 🟢 **DECIDED** | 2026-11-14 | Deferred |
| 12 | QUIL-9 | Document `flush()` caveat | 🟢 **DECIDED** | 2026-11-14 | Header + README |
| 13 | TOOL-13 | YAML + PyYAML via mise | 🟢 **DECIDED** | 2026-11-14 | mise config |
| 14 | TOOL-14 | Accept cmake-format sweep | 🟢 **DECIDED** | 2026-11-14 | cmake-format |

### Decision Details

#### Decision 1: DEF-3 — Comments Overstate Standard

**Question:** Do comments in `logging.cppm` and `internal.hpp` overstate the C++ standard regarding global module fragments?

**Decision:** 🔴 Open — Comments overstate the standard. The observed GCC/Clang failure is not the standard's rule.

**Rationale:**

- Comments in `logging.cppm:9-19` and `internal.hpp:4-8` state that global module fragments are "copied" into importing TUs and that standard headers would "collide"
- The C++ standard ( [module.global.frag] ) says the global module fragment is "imported" but does not specify the exact mechanism
- The observed collision (redefinition of `std::__is_constant_evaluated`) is an implementation detail of GCC/Clang, not a standard mandate
- Comment should reflect observed behavior, not standard mandate

**Options Considered:**

- (a) Remove comments entirely
- (b) Update comments to reflect observed behavior
- (c) Keep as-is (document the observed failure mode)

**Chosen:** (b) Update comments to reflect observed behavior, not standard rule

**Impact:** Comment-only fix in `logging.cppm:9-19` and `internal.hpp:4-8`

---

#### Decision 2: DEF-6 — Catalog IDs Renumber

**Question:** Catalog IDs renumber on every regeneration because ID = rank in text order.

**Decision:** 🔴 Open — Catalog IDs renumber on every regeneration.

**Rationale:**

- Current ID = rank in text order (position in source)
- `STABLE_JSON` not used for ID assignment
- ID change = wire format change (catalog IDs are wire identifiers)
- `BUILD-7` decision (a): CIB stable IDs needed

**Options Considered:**

- (a) Use `STABLE_JSON` for ID assignment
- (b) Assign IDs at first creation, never renumber
- (c) Use content-based hashing for ID generation

**Status:** Blocked on BUILD-7 decision (CI image)

**Impact:** Wire format stability — catalog IDs are wire identifiers

---

#### Decision 3: DEF-7 — Catalog Path Level Mapping Inverted

**Question:** Catalog path level mapping is inverted at both ends.

**Decision:** 🔴 Open — Mapping inverted at both ends.

**Rationale:**

- cib levels: MAX (most severe) → FATAL → ERROR → WARN → INFO → USER1 → USER2 → TRACE (most verbose)
- quill levels: TraceL3 (least) → TraceL2 → TraceL1 → Debug → Info → Warning → Error → Critical → TraceL3 (most)
- Current mapping in `cib_quill.hpp:68-88` inverts the order at both ends
- MAX→TraceL3 (least severe) but MAX is most severe
- TRACE→TraceL2 (2nd least) but TRACE is most verbose

**Options Considered:**

- (a) Invert mapping table
- (b) Add explicit mapping comments
- (c) Add compile-time assertions

**Impact:** Wrong severity in catalog path logs — critical severity logged as trace

---

#### Decision 4: DEF-8 — Formatter Section Header Names Wrong Function

**Question:** `format.hpp:473` says "formatter of whole message" but heads `parse_spec` function.

**Decision:** 🔴 Open — Comment-only fix.

**Rationale:**

- Section header at line 473 says "The formatter of a whole message"
- Actually heads `parse_spec` function (line 477) which parses a format specification
- The actual message formatter is `format_message` at line 532
- Comment-only fix: move section header from line 473 to line 532

**Impact:** Comment-only fix — move section header from line 473 to line 532

---

#### Decision 5: FMT-14 — Module Path Format Dialect

**Question:** Module path format dialect: document, validate, or move?

**Decision:** 🟢 **DECIDED (c)** — Move formatting out of module interface.

**Rationale:**

- Two format dialects: module = hand-rolled; Catalog = fmtquill
- Option (a): Document differences and live with divergence
- Option (b) Validate hand-rolled against fmt spec
- Option (c) Move formatting out of module interface (move `format.hpp` out of module purview)

**Chosen:** (c) Move formatting out of module interface

**Rationale:**

- Eliminates dialect divergence at source
- Single fmt implementation (fmtquill) for both paths
- Requires QUIL-1 (Codec N fields from 1 pack element) to succeed
- If QUIL-1 fails, fallback to (a) or (b)

**Dependencies:** QUIL-1 must succeed

**Impact:** Major refactor — move `format.hpp` out of module purview, use fmtquill for both paths

---

#### Decision 6: QUIL-9 — Document `flush()` Caveat

**Question:** Document `flush()` caveat in header + README.

**Decision:** 🟢 **DECIDED** — Document in header + README.

**Rationale:** `flush()` has static destructor hazard — static destructor may run before Quill backend shuts down, causing undefined behavior.

**Action:** Add caveat to `quill_logger.hpp` and `README.md`

---

#### Decision 7: TOOL-13 — YAML + PyYAML via mise

**Decision:** 🟢 **DECIDED** — YAML + PyYAML via mise.

---

#### Decision 8: TOOL-14 — Accept cmake-format Sweep

**Decision:** 🟢 **DECIDED** — Accept cmake-format sweep.

---

#### Decision 9: ENV-1 — Two fmt Copies Rule

**Decision:** 🟢 **DECIDED** — Two fmt copies rule: custom formatters for `fmt` only.

**Rationale:**

- `fmt` (standalone) and `fmtquill` (bundled in quill) are structural, not accidental
- Custom formatters written for `fmt` only; `fmtquill` uses its own internal formatters
- This is structural, not accidental

---

#### Decision 10: ENV-2 — Keep Coverage Build

**Decision:** 🟢 **DECIDED** — Keep `build/coverage-clang/` + document.

---

#### Decision 11: ENV-3 — Deferred

**Decision:** 🟢 **DECIDED** — Deferred (not a cpp-core decision).

---

#### Decision 12: QUIL-9 — Document `flush()` Caveat

**Decision:** 🟢 **DECIDED** — Document `flush()` caveat in header + README.

---

#### Decision 13: TOOL-13 — YAML + PyYAML via mise

**Decision:** 🟢 **DECIDED** — YAML + PyYAML via mise.

---

#### Decision 14: TOOL-14 — Accept cmake-format Sweep

**Decision:** 🟢 **DECIDED** — Accept cmake-format sweep.

---

### Decision Matrix

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
graph TD
    QUIL1[QUIL-1: Codec N fields?] --> FMT14c[FMT-14(c): move formatting]
    FMT14c --> STEP7[Plan Step 7: move formatting out]

    BUILD5[BUILD-5: no CI] --> TOOL16[TOOL-16: CI image]

    FMT13[FMT-13: feature-test macros] -.-> FMT14[FMT-14 decision]
    FMT14 --> FMT14c

    MOD11[MOD-11: GCC matrix] -.-> MOD6[MOD-6: --compile-std-module]
    MOD11 -.-> MOD1[MOD-1: GCC migration size]

    DEF1[DEF-1: level filter] --> COV2[COV-2: filter test]
    DEF7[DEF-7: catalog level map] --> COV7[COV-7: catalog path test]

    FMT15[FMT-15: must-not-compile] --> BUILD_LANE[Build lane reopen]

    QUIL1 -.->|If YES| STEP7
    QUIL1 -.->|If NO| FMT14ab[Fallback: FMT-14(a) or (b)]
```

## First 10 Steps When Lane Reopens

| Step | Action | Needs | Blocked By |
|------|--------|-------|------------|
| 1 | Fix the level-filtering defect (DEF-1) + test | Nothing | — |
| 2 | Add `"fmt"` to `vcpkg.json` | Nothing (already installed) | — |
| 3 | Mark `format.hpp` functions `constexpr` (15 functions) | Nothing — compiler is test | — |
| 4 | Add `static_assert` formatter tests | Step 3 | — |
| 5 | Replace `snprintf` with fmt in `format_double` | Nothing — fixes DEF-2, DEF-4 | — |
| 6 | Use `fmt::format` for cib tag string | Nothing | — |
| 7 | Move formatting out of module interface | **FMT-14(c)**, **QUIL-1** must succeed | QUIL-1 |
| 8 | Wire formatting into CMake | **TOOL-13**, **TOOL-14** | — |
| 9 | Coverage gate at 100% | Nothing (separate track) | — |
| 10 | `import std;` decision — keep status quo | Nothing — keep status quo | — |

```text
```
