# The module path reports no source location - review

**Status:** fixed. The module path now reports the call site's file and line, on both compilers,
without a macro.

**Scope:** item 2 of the two flagged items. Item 1 (the ASan leak check) is in
[`../asan-leak-check/`](../asan-leak-check/README.md).

**Question:** the log line's location field is empty for the messages that go through the module
path (`com::rsm::logging::info(...)`), while the catalog path (the `CIB_*` macros) reports it. The
module path has no macro, so how can it report the call site?

**Short answer:** it does not need a macro. A **default argument is evaluated at the call site**,
so a default argument of `__builtin_FILE()`, `__builtin_LINE()` and `__builtin_FUNCTION()` names the
caller's location. `format_string<>`'s constructor takes the location that way, and the location
travels with the format string into the logger.

The macro approach was measured first, and it does not work in a module: a macro defined in the
module's global module fragment does not reach the importing translation units, on either compiler.

---

## 1. The problem

The two logging paths share one quill logger and one pattern, so the location field is filled in
the same way for both. Before the fix:

```
14:31:39.170701250 [90840989] app.cpp:28                   LOG_INFO      cpp-core     [cpp_core id=1 mod=0] compile-time formatted: the answer is 42
14:31:39.170820875 [90840989]                               LOG_INFO      cpp-core     [] cpp-core: C++26 static reflection OK (point has 2 data members)
                                                                 ^^^^^^^^^^^^^ the module path: empty
```

The catalog path gets the location from the `CIB_*` macro, which expands to quill's
`log_statement` with `__FILE__` and `__LINE__`. The module path has no macro: it is a function in
a module interface, and a function cannot learn its call site.

The module's implementation (`src/logging/quill_logger.cpp`) passed empty strings and a zero line
number to quill:

```cpp
quill_logger()->template log_statement_runtime_metadata<true>(
    &metadata, "{}", "", "", "", 0U, to_quill_level(level), std::string{message, length});
//                             file  function  tags  line
```

## 2. What was measured

Every variant below is a complete, buildable program in [`repro/`](repro/); `repro/run.sh` builds
and runs all of them with clang-p2996 and GCC 16. The results:

| # | variant | clang-p2996 | GCC 16 | verdict |
|---|---|---|---|---|
| 1 | a macro in the module's global module fragment | `use of undeclared identifier 'GMF_MACRO'` | `'GMF_MACRO' was not declared in this scope` | **rejected**: the macro does not reach the importer |
| 2 | a macro in a header that the global module fragment includes | `use of undeclared identifier 'HDR_MACRO'` | same | **rejected**: same reason |
| 3 | `__builtin_FILE()` as defaulted parameters *after* a variadic pack | the runtime arguments are consumed by the location parameters: `no matching function for call to 'info'` | same | **rejected**: the shape does not work |
| 4 | `__builtin_FILE()` in `format_string`'s constructor's default arguments | `file=use.cpp line=4 function=run` | identical | **chosen** |

### 2.1 Why a macro does not work in a module

A macro is the usual way to capture a call site, and it is the reason the catalog path works. In a
module, the macro would have to be defined in the module's global module fragment, and the global
module fragment is not part of the module's interface: it is copied into every translation unit
that imports the module, but its *macros* are not exported with it.

```
use.cpp:4:22: error: use of undeclared identifier 'GMF_MACRO'
```

That is the same on both compilers. The declarations of the global module fragment do not reach
the importer either (measured: a struct declared in the fragment is "not declared in this scope"
in the importer), so the fragment is not a channel for anything but the implementation.

The other way to get a macro to the importers - a header that both the module and the importers
include - collides with the module's design: the header would be included twice, once in the
global module fragment and once in the importer, and the two copies would be different entities.
That is exactly why the module's interface is free of the standard library (see the top of
`modules/logging/logging.cppm` and `include/cpp-core/logging/internal.hpp`).

### 2.2 The defaulted-parameter trick

A default argument is evaluated in the context of the *call*, not in the context of the
declaration. So the builtins in a default argument name the caller:

```cpp
template <unsigned long N>
consteval format_string(char const (&text)[N], char const *file = __builtin_FILE(),
                         unsigned line = __builtin_LINE(),
                         char const *function = __builtin_FUNCTION())
```

`format_string<>` is constructed at the call site of `info(...)`, so the location it stores is the
caller's. `log()` then hands it to the implementation, which passes it to quill:

```cpp
detail::emit(static_cast<int>(l), fmt.file, fmt.line, fmt.function, buffer.data(), buffer.size());
```

The file and the function name are string literals with static storage duration, so quill's
shallow copy of them stays valid (see `upstream/quill/core/MacroMetadata.h`:
`LogWithRuntimeMetadataShallowCopy`).

The same trick works for `log_raw()`, which takes the location as defaulted parameters of its
own.

### 2.3 The variant that does not work

The obvious shape - defaulted location parameters after the variadic pack - does not work, because
a defaulted parameter after a pack is part of the pack's deduction: the runtime arguments end up
in the location parameters (`repro/v3_variadic_trailing_defaults/`).

```
use.cpp:4:3: error: no matching function for call to 'info'
mD.cppm:19:6: note: candidate function template not viable: no known conversion from 'int' to 'const char *' for 2nd argument
```

Capturing the location in the *format string* avoids the problem, because the format string is the
first parameter and the runtime arguments keep their place.

## 3. The change

| File | Change |
|---|---|
| `modules/logging/logging.cppm` | `format_string<>`'s constructor takes the location as defaulted parameters and stores it; `log_raw()` takes the same defaulted parameters; `log()` forwards the format string's location to the implementation. |
| `include/cpp-core/logging/internal.hpp` | `emit()` takes the file, the line and the function name. |
| `src/logging/quill_logger.cpp` | `emit()` passes them to quill's `log_statement_runtime_metadata` instead of `""`, `""` and `0U`. |
| `tests/logging_test.cpp` | Two tests check that a formatted call and a raw call report `logging_test.cpp:<line>`. |

## 4. Verification

The application, before and after (the module path is the last line):

```
before:  14:31:39.170820875 [90840989]                               LOG_INFO      cpp-core     [] cpp-core: C++26 static reflection OK (point has 2 data members)
after:   14:31:39.170820875 [90840989] reflection_demo.cpp:27       LOG_INFO      cpp-core     [] cpp-core: C++26 static reflection OK (point has 2 data members)
```

Both compilers:

```
$ ./build/p2996-debug/cpp-core | tail -1
$ ./build/gcc16-debug/cpp-core | tail -1
```

The whole preset matrix passes:

```
$ for w in gcc16-debug gcc16-release gcc16-asan p2996-debug p2996-release p2996-asan p2996-tsan p2996-iwyu; do
      cmake --workflow --preset $w
  done
```

The two new tests fail without the fix (the fix reverted, the rest of the tree unchanged):

```
FAILED "a formatted log call carries the source location of the call" .../cpp-core/tests/logging_test.cpp:137
FAILED "a raw log call carries the source location of the call" .../cpp-core/tests/logging_test.cpp:154
tests: 8 (6 passed, 2 failed, 0 compile-time)
```

## 5. Notes for the next person

A malformed format string inside the `ut` suite is reported in a way that points somewhere else.
The suite's initializer is evaluated at compile time, and the `consteval` constructor's throw is
reported as:

```
ut.hpp:369:29: error: call to immediate function '(anonymous class)::operator()' is not a constant expression
logging_test.cpp:17:5: note: non-constexpr function 'set_level' cannot be used in a constant expression
```

The note points at the first non-constexpr call in the suite, not at the format string. The same
call outside the suite names the real cause:

```
error: call to consteval function 'com::rsm::logging::format_string<int>::format_string<6UL>' is not a constant expression
note: in call to 'format_string<6UL>("probe")'
```

## Reproducing

```sh
docs/module-source-location/repro/run.sh
```

The script builds every variant of [`repro/`](repro/) with clang-p2996 and GCC 16 and prints what
each one reports. It needs both compilers on PATH (the same names the presets use).
