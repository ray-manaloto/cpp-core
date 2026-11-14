---
okf_version: "0.2"
title: Module Source Location Research
description: How the module path reports call-site source location without a macro, using defaulted parameters with __builtin_FILE/LINE/FUNCTION
version: 1.0.0
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - module
  - source-location
  - cpp26
  - clang
  - gcc
  - cpp-core
  - logging
sources:
  - id: source-document
    resource: https://github.com/ray-manaloto/cpp-core/blob/main/docs/module-source-location/README.md
    title: Original Module Source Location Documentation
    author: human:ray-manaloto
    last_modified: 2026-11-14T00:00:00Z
---

## Module Source Location Research

How the module path (`com::rsm::logging::info(...)`) reports the call site's file, line, and function without a macro - using defaulted parameters evaluated at the call site.

### Quick Summary

**Problem**: Module path log lines had empty location fields, while catalog path (CIB macros) reported file/line.

**Solution**: Default arguments evaluated at call site using `__builtin_FILE()`, `__builtin_LINE()`, `__builtin_FUNCTION()` - captured in `format_string<>` constructor, travels with format string to logger.

**Result**: Both compilers (clang-p2996, GCC 16) now report correct call site:

```text
before:  14:31:39.170820875 [90840989]                               LOG_INFO      cpp-core     [] cpp-core: C++26 static reflection OK
after:   14:31:39.170820875 [90840989] reflection_demo.cpp:27       LOG_INFO      cpp-core     [] cpp-core: C++26 static reflection OK
```

### Key Findings

#### Why Macros Don't Work in Modules

| Attempt | Result |
|---------|--------|
| Macro in global module fragment | `use of undeclared identifier` - macros don't reach importers |
| Macro in included header | Same - global module fragment declarations not exported |
| Defaulted params after variadic pack | Runtime args consumed by location params - type mismatch |
| **Defaulted params in `format_string` constructor** | **Works** - format string is first param, args keep their place |

The global module fragment is **not** a channel for macros or declarations to reach importing translation units - it's copied but its macros are not exported.

#### The Working Pattern

```cpp
// In module interface (logging.cppm)
template <unsigned long N>
consteval format_string(char const (&text)[N],
                        char const *file = __builtin_FILE(),
                        unsigned line = __builtin_LINE(),
                        char const *function = __builtin_FUNCTION()) {
    // file/line/function are evaluated at CALL SITE
}

// log() forwards format_string's location to implementation
void log(level l, format_string<> fmt, auto&&... args) {
    detail::emit(static_cast<int>(l), fmt.file, fmt.line, fmt.function, ...);
}
```

#### Implementation Changes

| File | Change |
|------|--------|
| `modules/logging/logging.cppm` | `format_string<>` constructor takes location as defaulted params; `log_raw()` same; `log()` forwards location |
| `include/cpp-core/logging/internal.hpp` | `emit()` takes file, line, function name |
| `src/logging/quill_logger.cpp` | `emit()` passes to quill's `log_statement_runtime_metadata` instead of empty strings |
| `tests/logging_test.cpp` | Two tests verify formatted and raw calls report correct `logging_test.cpp:<line>` |

### Verification

#### Preset Matrix (All Pass)

```sh
for w in gcc16-debug gcc16-release gcc16-asan \
         p2996-debug p2996-release p2996-asan p2996-tsan p2996-iwyu; do
  cmake --workflow --preset $w
done
```

#### Tests Fail Without Fix

```sh
# With fix reverted:
FAILED "a formatted log call carries the source location of the call"
FAILED "a raw log call carries the source location of the call"
tests: 8 (6 passed, 2 failed, 0 compile-time)
```

### Reproduction

```sh
docs/module-source-location/repro/run.sh
```

Builds and runs all 4 variants with both compilers:

1. Macro in GMF → rejected
2. Macro in header → rejected
3. Defaulted params after pack → rejected
4. **Defaulted params in format_string constructor** → chosen ✅

### Notes for Future Work

#### UT Suite Format String Errors

Malformed format strings inside `ut` suites report misleadingly - the `consteval` constructor's throw points to the first non-constexpr call in the suite, not the actual format string. Outside the suite, the error correctly names the format string.

```text
# Inside ut suite (misleading):
ut.hpp:369: error: call to immediate function 'operator()' is not a constant expression
logging_test.cpp:17: note: non-constexpr function 'set_level' cannot be used...

# Outside suite (correct):
error: call to consteval function 'format_string<6UL>::format_string<6UL>("probe") is not a constant expression
```

### Related

- [Architecture Bundle → Component Diagram → Data Flow — Module Path](../architecture/01-component-diagram.md#data-flow--module-path)
- [ASAN Leak Check](../asan-leak-check/index.md) - Other flagged item
- [Project Root PARKED.md](../../PARKED.md)
