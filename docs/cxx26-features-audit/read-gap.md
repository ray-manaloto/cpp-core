# The read gap, closed

**Date:** 2026-11-13
**Status:** research. The reading is done. The build lane is still parked, so nothing here is
applied to the code.

**What this part is.** The measurement harness counts the library's source lines the audit has
read at line granularity - cited with a line number, not merely named as a file
(`scripts/measure.py`; the `audit.read_coverage_share` metric in
[measurements.md](measurements.md)). On 2026-11-12 that share was **0.633**: 895 of 1415 lines,
with **520 lines** read by nobody.

This part is the record of the pass that closed the gap. Every one of those 520 lines is listed
below, file by file, largest gap first, with what the lines say and what the reading found. The
pass found six things the audit had not seen, and each is recorded here and in the part it
belongs to:

1. **a new defect** - `DEF-7`, the catalog path's level mapping is inverted at both ends
   ([open-items.md](open-items.md));
2. **a missing function name** on the catalog path, which quill's `%(caller_function)` attribute
   would have shown;
3. **a dead assignment** in the formatter, which made a coverage-table row describe a branch that
   does nothing;
4. **a coverage table that said what to log but not what to assert** - four of the eight existing
   tests assert `expect(true)`;
5. **a counterexample to the audit's own module matrix** - the project's own test translation
   unit imports the module *and* includes six standard headers, and it builds;
6. **a misplaced section header** in the formatter, which names a function 59 lines away
   (`DEF-8`).

**The method.** Read the source, line by line, in the order the files are listed. Where a line
made a claim about a third-party library, the claim was checked against the installed header, and
the header is cited. Where a line was a claim about the standard, the standard is cited as the
other parts cite it. **No build, no compiler, no CMake, no test** - the lane is parked, and
anything that would need a compile is written down as an open item instead.

**The library is byte-identical to the baseline.** This pass moved the process, not the code.

## 1. What the gap was

| File | Lines | Read | Unread |
|---|---|---|---|
| `tests/logging_test.cpp` | 162 | 37 | 125 |
| `modules/logging/format.hpp` | 602 | 502 | 100 |
| `include/cpp-core/logging/cib_quill.hpp` | 171 | 105 | 66 |
| `modules/logging/logging.cppm` | 153 | 105 | 48 |
| `include/cpp-core/logging/internal.hpp` | 55 | 8 | 47 |
| `src/logging/quill_logger.cpp` | 169 | 124 | 45 |
| `src/reflection_demo.cpp` | 31 | 3 | 28 |
| `src/app.cpp` | 35 | 10 | 25 |
| `include/cpp-core/logging/quill_logger.hpp` | 20 | 0 | 20 |
| `src/main.cpp` | 17 | 1 | 16 |
| **total** | **1415** | **895** | **520** |

## 2. `tests/logging_test.cpp` - the suite

The gap was almost three quarters of the file, and it was the biggest gap in the project: the
audit knew what the tests *did* and had never read *how* they do it.

| Lines | What they say | What the reading found |
|---|---|---|
| `tests/logging_test.cpp:1-8` | the file's header comment: the tests use `ut` "the same way glaze does", and "the import comes first: an import declaration has to precede every other declaration of the translation unit" | the comment is about the **import**, not the includes - and the file then includes three standard headers after the import (`:13-15`). That is the shape the audit's matrix says fails on GCC 16 |
| `tests/logging_test.cpp:9-12` | `import com.rsm.logging;`, then `#include "ut/ut.hpp"` | the module is imported and `ut` is included **textually**. The installed `ut` 1.2.1 header includes six standard headers - `<concepts>`, `<cstdint>`, `<cstdlib>`, `<iostream>`, `<source_location>`, `<string_view>` - so this translation unit mixes an import with six standard headers. **It builds.** Part 18's matrix says that shape fails on GCC 16 (`import-std.md:188`); the project's own test file is the counterexample, and `MOD-11` is the open question that says so |
| `tests/logging_test.cpp:16-25` | `using namespace ut;`, the anonymous namespace, and the comment on the capture: "The sink writes to the stdout stream, so the capture redirects the file descriptor of stdout to a temporary file and puts it back afterwards" | the capture works at the **file-descriptor** level, not at the `std::cout` level, because quill's console sink writes to the C `stdout` stream |
| `tests/logging_test.cpp:44-73` | the rest of `stdout_capture` (the destructor, `ok()`, `contents()`), the end of the anonymous namespace, and the start of the `suite` | the destructor flushes stdout, restores the saved descriptor with `dup2` and closes it; `contents()` flushes, rewinds the temporary file and reads up to 4095 bytes into a stack buffer. The capture is **per-test and stack-allocated**, and it restores the descriptor in its destructor - so a test that fails an assertion still restores stdout |
| `tests/logging_test.cpp:82-91` | the test "the levels are ordered from the least to the most severe" | it asserts the **order** of the enum's values (`trace` < `debug` < `info` < `warning` < `error` < `critical`), and nothing else. It says nothing about what those levels *do* |
| `tests/logging_test.cpp:99-162` | the six remaining tests and `int main() {}` | **four of the six assert `expect(true)`** - "logging a message does not throw" (`:97`), "a message can be logged with every kind of value" (`:111`), "a message that is already formatted can be logged" (`:117`) and "the format string is checked at compile time" (`:124`). The two source-location tests do assert (`:140`, `:157`), and the level round-trip test does (`:76`, `:80`). `int main() {}` at `:162` is empty, because `ut`'s own `main` is not used: the suite is a global object |

**What this means.** The suite proves the library **does not throw** and that the source location
is **right**. It proves nothing about what any message says. Six of the eight tests would pass
against a logger that discarded every message it was given.

That is the gap part 7 (the coverage plan) had to close, and it is why the plan's table now says
what each test must **assert**, not merely what it must log.

## 3. `modules/logging/format.hpp` - the module's private formatter

| Lines | What they say | What the reading found |
|---|---|---|
| `format.hpp:1-3` | the opening comment: "the module-private formatting helpers of the logging module" | the file is **private by construction**, not by convention - it is included inside the module purview (`logging.cppm:33`), so nothing outside the module can reach it |
| `format.hpp:7-19` | the rest of the header comment (the format follows the shape of `std::format`; the supported specifications are `[[fill]align][sign][#][0][width][.precision][type]`), `#pragma once`, the namespace opening, and the type-traits section header | the comment states the **structure**, and part 13 shows it implements the **specification** loosely. The list of supported specifications is the grammar the parser actually accepts |
| `format.hpp:105-106` | `is_signed_v` - `T(-1) < T(0)` - and the blank line after it | the unsigned wrap-around makes this false for an unsigned type, which is why the smallest value's negation is done in unsigned arithmetic later (`format.hpp:359-362`) - and why the test "a negative integer" is the one that exercises it |
| `format.hpp:107-124` | the three concepts: `convertible_to`, `string_like` (a `c_str()` and a `size()`), `self_formatting` (a `format_to(buffer, capacity)` member), and the blank line after them | `string_like` is how `std::string` and `std::string_view` are formatted **without naming them** - the module's interface may not name standard-library types, so it recognises them by shape instead. `self_formatting` is the extension point the project has no user of |
| `format.hpp:125-149` | `forward` (the two overloads) and `field_spec` - the nine members of a parsed specification: `fill`, `align`, `sign`, `alternate`, `zero_pad`, `width`, `precision`, `type`, `default_align` - and the blank line after them | `default_align` is the interesting one: it is the **type-dependent** default alignment (`<` for strings and `bool`, `>` for numbers), and it is the reason the parser can be type-agnostic while the output still matches the standard's Table 104 |
| `format.hpp:153` | the blank line before `message_buffer` | - |
| `format.hpp:207-218` | the blank line, the scanner's section comment and `scan_result` - `fields`, `max_index`, `valid`, `manual_index` | the scanner is a `consteval` function, so it produces no runtime arcs. `manual_index` is the flag that rejects mixing automatic and manual indexing (`format.hpp:276-279`) |
| `format.hpp:295-300` | the blank line, the comment before the value formatters, and `copy_text`'s signature | `copy_text` is the only place a string is copied, and it is where both the precision branch and the capacity branch live |
| `format.hpp:313-327` | the blank line, `string_length` (a null-terminated string) and `digit_char` (two 16-entry digit tables) | `digit_char`'s tables are `constexpr char[]` inside the function, so the uppercase table is a **separate 17-byte object** from the lowercase one; `format.hpp:325-326` is the coverage row that logs `"{:X}"` |
| `format.hpp:328` | the blank line before `format_integer` | - |
| `format.hpp:422` | the blank line before `format_value` | the comment is at `format.hpp:423` |
| `format.hpp:464-471` | the blank line, then `argument_value` - "the address of the argument itself. The formatter knows the type of the argument, so it reads the object at that address - an array is read as an array, not as a pointer" | this is the type-erasure mechanism the whole formatter rests on: the pack is flattened into two parallel arrays, a function pointer per type and the address of each argument (`format.hpp:537-540`) |
| `format.hpp:472-476` | the blank line, the section header "The formatter of a whole message" - and then the comment "Parses a format specification" | **the section header is misplaced.** It heads `parse_spec`, not `format_message`; `format_message` is at `format.hpp:532`. A **sixth** finding, and the smallest one - it is `DEF-8` |
| `format.hpp:515-530` | `append_escaped` - the unescaping of `{{` and `}}` | this is the **only** place the escapes are handled for a message with no arguments; the field loop handles its own (`format.hpp:547-550`, `:587-590`). Two copies of the same rule, in two functions |
| `format.hpp:601-602` | the closing namespace | - |

**The dead assignment.** `format.hpp:399-401` clamps a `total` that is never read again:

```cpp
if (total >= capacity) {
  total = capacity - 1U;
}
```

`total` is not used after this - the writes are bounded by the `at < capacity` guards at
`format.hpp:404`, `:407` and `:410` instead. So the "truncation at the capacity" branch
computes a length and throws it away. Part 7's coverage table listed it as a branch to cover;
the reading says it is a **no-op**, and the test that covers the real behaviour is "log a very
wide integer", which exercises the `at < capacity` guards.

## 4. `include/cpp-core/logging/cib_quill.hpp` - the catalog path

| Lines | What they say | What the reading found |
|---|---|---|
| `cib_quill.hpp:1-23` | the file's header comment: the two parts of cib's logging, the "binary loggers" model, and the ODR note ("every translation unit that logs must see the same specialization of `logging::config<>`") | the ODR note is the reason the header defines `logging::config<>` as an explicit specialization (`cib_quill.hpp:169-171`) rather than leaving it to the application to pick |
| `cib_quill.hpp:41-44` | the namespace opening and the comment on `level_of` | - |
| `cib_quill.hpp:52-54` | the blank line, and the comment on `decay_enum_value` - "fmt (and therefore quill) cannot format a scoped enum that has no formatter of its own" | this is the reason the catalog path decays its one project type to its underlying integer, and the reason a custom formatter is written for `fmt` only |
| `cib_quill.hpp:62-63` | the blank line, and the comment that begins the level mapping: "cib's levels follow the MIPI Sys-T severity scale (0 = most severe, 7 = most verbose); quill's scale runs the other way (higher = more severe). This mapping preserves the relative order" | **the comment is wrong, and so is the mapping.** It is the finding `DEF-7` |
| `cib_quill.hpp:89-107` | `string_type`, `message_type_t` - the catalog's string and message types | the format string becomes **part of the message's type**, so the string data never reaches the payload; the catalog tooling assigns an ID to each distinct type (`sc::undefined<sc::args<Args...>, -1, ...>`) |
| `cib_quill.hpp:117-126` | `module_type_t` and the comment on `quill_config` | the module name is kept in a `static constexpr` so that the characters have static storage duration - "a string_view of a temporary would not be a constant expression" |
| `cib_quill.hpp:164-171` | the closing namespace, the ODR comment, and the `logging::config<>` specialization | - |

### 4.1 `DEF-7` - the level mapping is inverted at both ends

The mapping is at `cib_quill.hpp:68-88`. The two scales are:

| | The scale | Where |
|---|---|---|
| cib | `MAX = 0` (most severe) … `TRACE = 7` (least severe) | `log/level.hpp:8-17` |
| quill | `TraceL3` (least severe) … `Critical` (most severe) | `quill/core/LogLevel.h:26-44` |

The mapping sends cib's **most severe** level to quill's **least severe** one, and cib's **least
severe** level to quill's second-least severe one:

| cib | quill | Severity, on quill's scale |
|---|---|---|
| `MAX` | `TraceL3` | **least severe** - the bottom of the whole scale |
| `FATAL` | `Critical` | **most severe** - the top of the whole scale |
| `ERROR` | `Error` | severe |
| `WARN` | `Warning` | - |
| `INFO` | `Info` | - |
| `USER1` | `Debug` | - |
| `USER2` | `TraceL1` | - |
| `TRACE` | `TraceL2` | second least severe |

The comment above the mapping prints the two scales side by side and says the mapping "preserves
the relative order" (`cib_quill.hpp:63-67`). Its own table puts quill's order as
`TrL3 Crit Error Warn Info Debug TrL1 TrL2` - that is, it treats `TrL3` as quill's most severe
level. Quill says the opposite: "TraceL3 is the most detailed trace level", and `Critical` is the
top of the scale (`quill/core/LogLevel.h:26-44`).

**What it costs.** The sink drops anything less severe than its threshold
(`quill/sinks/Sink.h:204`: `if (log_level < _log_level.load(...)) return false;`). With a sink at
`Error`, a `MAX` message is **dropped** and a `FATAL` message is **kept** - the exact opposite of
the intent. The two ends of the scale are swapped.

**Reachability.** `CIB_LOG_WITH_LEVEL(logging::level::MAX, ...)` reaches it
(`log/log.hpp:66-69`). The project never logs at `MAX` - the three calls in `src/app.cpp:27-30`
are `CIB_INFO`, `CIB_WARN` and `CIB_ERROR` - so **nothing misbehaves today**. It is a latent
defect, and it is one line of mapping to get wrong.

**Why it is not a one-line fix.** quill has exactly one level more severe than `Error`
(`Critical`), so eight cib levels cannot map one-to-one onto quill's ten; the mapping has to
decide which cib levels share a quill level, and the two ends are where it goes wrong. The fix
belongs with `DEF-1` (the level filter does not work at all) and with the level table in part 2.

### 4.2 The catalog path carries no function name

`quill::Logger::log_statement_runtime_metadata` takes the function name as its **fourth**
parameter (`quill/Logger.h:427-433`):

```cpp
log_statement_runtime_metadata(MacroMetadata const* macro_metadata, char const* fmt,
                                char const* file_path, char const* function_name,
                                char const* tags, uint32_t line_number, LogLevel log_level, ...)
```

The module path passes the real one (`src/logging/quill_logger.cpp:117-118`: `file, function`).
The catalog path passes an **empty string** (`cib_quill.hpp:157-159`: `file, ""`).

**The cause is upstream.** cib's `CIB_LOG` hands the customization point only the file and the
line (`log/log.hpp:63-64`):

```cpp
#define CIB_LOG(...) \
    logging::log<cib_log_env_t>(__FILE__, __LINE__, STDX_CT_FORMAT(__VA_ARGS__))
```

There is no function name in the interface, so there is none to pass. **No visible effect today**
- the project's pattern prints `%(short_source_location)`, not `%(caller_function)` - but quill's
`%(caller_function)` attribute would show the module path's function and nothing at all for the
catalog path. Part 6's option (e) (`std::source_location::current()`) is the way to fix it, and
part 2's `MAC-1` is the open question about whether it works through cib's template.

## 5. `include/cpp-core/logging/internal.hpp` - the standard-library-free bridge

| Lines | What they say | What the reading found |
|---|---|---|
| `internal.hpp:1-2` | the opening comment: "the interface between the logging module and its implementation" | the header is **the boundary**. Everything on one side of it is standard-library-free, and everything on the other side is free |
| `internal.hpp:3-53` | the two compiler errors the rule avoids, the six integer level constants (`:22-27`), the six function declarations (`start_logger`, `flush_logger`, `set_log_level`, `get_log_level`, `emit`, `format_double`) and their comments | **the header includes nothing at all** - no `#include`, not even a standard one. That is what makes it safe to put in the module's global module fragment, and it is why the module's global fragment contributes no standard headers to the importing translation unit |
| `internal.hpp:54-55` | the closing namespace | - |

**The levels are plain integers** (`:22-27`), 0 to 5, from `trace_level` to `critical_level`. The
module's own `level` enum lives in the module's purview, so this interface - which is in the
global module - cannot name it; it uses `int` instead, and the module casts in both directions
(`logging.cppm:92`, `:95`).

**`emit` takes plain values** (`:46-47`): the level as an `int`, the file and the function as
`char const*`, the line as an `unsigned`. The comment explains why the pointers are safe: "The
file and the function name are string literals with static storage duration (they come from
`__builtin_FILE()` and `__builtin_FUNCTION()`), so they outlive the call." That is the whole
reason the module can pass a source location without naming `std::source_location`.

**`format_double` is on the other side of the boundary** (`:52-53`) - it takes a `double` and a
`char*` and returns a length. It is a plain function, not a template, so it lives in the
implementation translation unit and the module calls it through this declaration.

## 6. `modules/logging/logging.cppm` - the module interface

| Lines | What they say | What the reading found |
|---|---|---|
| `logging.cppm:1-8` | the module's header comment: the usage (`import com.rsm.logging;` then `com::rsm::logging::info(...)`) | - |
| `logging.cppm:20-27` | the end of the header comment (the catalog path), `module;`, and the blank line after it | `module;` opens the **global module fragment**. The include of the internal header is at `logging.cppm:28`, inside it, so its declarations are attached to the global module and are shared with the implementation translation unit - which is exactly what the header's own comment says (`internal.hpp:13-14`). And because `internal.hpp` includes nothing, **the module's global fragment contributes no standard headers at all** |
| `logging.cppm:29-32` | `export module com.rsm.logging;` and the comment "The module's private implementation" | `export module` closes the global module fragment. `#include "format.hpp"` comes **after** it, so the formatter is in the module's purview and is not reachable by an importer |
| `logging.cppm:34-46` | `export namespace com::rsm::logging {` and the `level` enum | the enum is `unsigned char` with six values, `trace = 0` to `critical = 5` - the same order as the integer constants in `internal.hpp` |
| `logging.cppm:50-58` | the comment on `format_string`: the `consteval` constructor, the source location, and "That is how the module path gets a source location without a macro" | the comment says a macro "cannot be used because a macro defined in this module's global module fragment is not visible in the importing translation units (clang and GCC both drop it)". The default-argument idiom is the whole trick |
| `logging.cppm:61-63` | the comment on the template parameter: each argument is wrapped in a `type_identity` "so that the format string is not used to deduce them" | this is why `format_string<detail::type_identity_t<Args>...>` can be a parameter of `log` without the format string participating in deduction |
| `logging.cppm:84-86` | the `setup` declaration and its comment | the module's whole public surface is a thin forwarding layer: `setup`, `flush`, `set_level`, `current_level`, `log_raw`, `log` and the six level-named wrappers |
| `logging.cppm:152-153` | the closing namespace | - |

**What this settles.** The module interface is **19 lines of interface and 9 of declarations**, and
it reaches the implementation through six plain declarations in a header that includes nothing.
The audit's rule - "the module interface stays free of the C++ standard library" - is not a
convention; it is a property of `internal.hpp` having no `#include` in it.

## 7. `include/cpp-core/logging/quill_logger.hpp` - the one declaration the catalog path needs

| Lines | What they say | What the reading found |
|---|---|---|
| `quill_logger.hpp:1-20` | the whole header: the comment that says "This header is used by the `CIB_*` macro path (cpp-core/logging/cib_quill.hpp), which calls quill's templated API directly", and the one declaration, `auto quill_logger() -> quill::Logger *;` | the header is **20 lines and declares one function**. The module path does not use it - the module reaches the implementation through `internal.hpp`. The catalog path does use it, because the catalog path is allowed to name quill |

**And it is not standard-library-free** - it includes `<quill/Logger.h>` (`:13`). That is fine,
because the catalog path is not the module: `internal.hpp` is the boundary, and the catalog path
is outside it.

## 8. `src/logging/quill_logger.cpp` - the implementation

| Lines | What they say | What the reading found |
|---|---|---|
| `quill_logger.cpp:1-35` | the file's header comment, the two includes of the project's own headers, quill's headers, the standard headers, the namespace opening, and the three constants (`logger_name`, `sink_id`, `pattern`) | the pattern is `"%(time) [%(thread_id)] %(short_source_location:<28) LOG_%(log_level:<9) %(logger:<12) [%(tags)] %(message)"` - it prints the **short source location**, never the function name. That is why the missing function name on the catalog path has no visible effect today |
| `quill_logger.cpp:36` | the blank line before `to_quill_level` | - |
| `quill_logger.cpp:74-82` | the end of `from_quill_level` (the `Backtrace` / `None` cases and the fallback to `info_level`), the closing of the anonymous namespace | the fallback is `info_level`, and the module's `level` enum has no value for `Backtrace` or `None` - so those two cases are unreachable from the module |
| `quill_logger.cpp:92-99` | `start_logger` and `flush_logger` | `start_logger` is `(void)quill_logger();` - it starts the backend by creating the logger |
| `quill_logger.cpp:99-100` | the end of `flush_logger` and the blank line after it | - |
| `quill_logger.cpp:101-102` | `set_log_level` and the blank line after it | `set_log_level` calls `quill_logger()->set_log_level(to_quill_level(level))` - the **logger's** threshold, which is what `DEF-1` is about |
| `quill_logger.cpp:103-104` | `get_log_level` and the blank line after it | - |
| `quill_logger.cpp:120` | the blank line before `format_double` | - |
| `quill_logger.cpp:168-169` | the closing namespace | - |

**The module path's level mapping is correct** (`quill_logger.cpp:37-55`): `trace` to `TraceL2`,
`debug` to `Debug`, `info` to `Info`, `warning` to `Warning`, `error` to `Error`, `critical` to
`Critical`. The defect is only in the catalog path's separate mapping (`DEF-7`).

**`format_double` is the other side of the boundary** (`quill_logger.cpp:121-167`) and is the
only place the standard library's `snprintf` is used. Its `'f'` case is **DEF-2**.

## 9. `src/app.cpp` - the catalog path's application

| Lines | What they say | What the reading found |
|---|---|---|
| `app.cpp:1-21` | the file's header comment ("The log calls live here (and not in main.cpp), so that the string catalog tooling can scan the object files"), the include of `cib_quill.hpp`, the `demo` namespace, the declaration of `reflection_demo`, and `CIB_LOG_MODULE("cpp_core")` with its comment | the comment on `CIB_LOG_MODULE` explains a real constraint: it "declares `cib_log_env_t` in the enclosing namespace (it shadows the global alias of that name), so it goes inside a namespace rather than at global scope". The module name is `"cpp_core"` - and the **catalog's module ID** is derived from it (`cib_quill.hpp:108-120`) |
| `app.cpp:31-35` | `reflection_demo();` and the closing namespace | the application calls the reflection demo, and the demo's message is on the **module path** - so one executable exercises both paths, and the module path is reached from a translation unit that includes `cib_quill.hpp` |

**The three catalog calls** (`app.cpp:27-30`) are `CIB_INFO` with a **compile-time** argument
(`constexpr auto answer = 42`), `CIB_WARN` with a runtime argument, and `CIB_ERROR` with none.
That is the whole of the catalog path's use in the project - which is why the level mapping's
`MAX` case is never reached.

## 10. `src/main.cpp` - the entry point

| Lines | What they say | What the reading found |
|---|---|---|
| `main.cpp:1-14` | the header comment ("The main is a stub: the log calls live in the application library, so that the string catalog tooling can find them"), `import com.rsm.logging;`, the declaration of `demo::run`, and `main()` | `main` is on the **module path** - it imports the module - while the log calls it makes (`setup`, `flush`) are the module's. The catalog path is reached only through `demo::run()`, which is a **separate library** (`src/app.cpp`) |
| `main.cpp:16-17` | `return 0;` and the closing brace | - |

**One executable, two paths, and they never meet in a translation unit.** `main.cpp` imports the
module; `app.cpp` includes `cib_quill.hpp` and does not import it. That is the shape `MOD-10`
describes.

## 11. `src/reflection_demo.cpp` - the reflection demo

| Lines | What they say | What the reading found |
|---|---|---|
| `reflection_demo.cpp:1-22` | the file's header comment (its own translation unit, because the reflection header is not part of the standard library the include-what-you-use checks use), `import com.rsm.logging;`, `#include <meta>`, the `demo` namespace, `struct point`, and `reflection_demo()` | the header comment says the checks "run with the Homebrew toolchain, whose standard library has no reflection header yet". **This is the one translation unit that imports the module and includes a standard header** (`<meta>`) - and it is a *different* standard header from the six the test file picks up through `ut` |
| `reflection_demo.cpp:26-31` | the `info` call and the closing namespace | the `static_assert(member_count == 2)` at `:25` is the **compile-time** half of the reflection check; the `info` call is the run-time half. The comment above it - "GCC 16's member range cannot outlive constant evaluation, so call size() on the temporary" - is a real portability constraint, written down |

## 12. What the pass changed in the other parts

| Part | What changed |
|---|---|
| 1 - [README.md](README.md) | the defect table gains **DEF-7** and **DEF-8**; the "honest 100% coverage" section now says what the eight tests actually assert; the open-item counts are corrected |
| 2 - [intel-libraries.md](intel-libraries.md) | the cib level table is corrected, with the two scales side by side |
| 6 - [macro-reduction.md](macro-reduction.md) | the catalog path's missing function name is recorded against option (e) |
| 7 - [coverage-gaps.md](coverage-gaps.md) | every row now says what the test must **assert**; the dead "truncation at the capacity" row is corrected; the four `expect(true)` tests are named, one by one |
| 8 - [quill-runtime-formatting.md](quill-runtime-formatting.md) | the catalog path's empty function name is recorded, next to `DEF-1` |
| 9 - [constexpr-and-fmt.md](constexpr-and-fmt.md) | the dead assignment in `format_integer` is recorded, next to **DEF-8** |
| 10 - [open-items.md](open-items.md) | **DEF-7** and **DEF-8** are new open items |
| 13 - [format-dialect.md](format-dialect.md) | the parser's grammar is completed - the six branches it really has, read line by line |
| 15 - [catalog-ids.md](catalog-ids.md) | the catalog path's identifiers are traced from `app.cpp` to the queue |
| 19 - [measurements.md](measurements.md) | the read-coverage table is corrected (the denominator was wrong) and the share is now 1.0 |

## 13. What the pass did not do

- **It did not build anything.** The build lane is parked; no compiler was invoked, no preset was
  run, no test was executed. Every claim here is read from the source or from an installed
  header.
- **It did not change the library.** The source is byte-identical to the baseline. The pass moved
  the audit, not the code.
- **It did not settle what needs a compile.** The 68 compile/run/preprocessor items are still
  open, and the pass added no new ones of that kind: `DEF-7` is settled by reading, not by
  running.
- **It did not make the coverage plan executable.** The plan in part 7 says what each test must
  assert; writing those tests needs the build lane.
