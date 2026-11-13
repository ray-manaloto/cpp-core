# What the tests do not reach

**Date:** 2026-11-11
**Status:** research. Derived by reading the source, **not** measured - the coverage gate does not
exist yet. It is the hypothesis that the first measurement must confirm or correct.

**Why this matters:** the 100% coverage target is only meaningful if the denominator is known. A
coverage gate that reports "100%" over a denominator that silently excludes the hard parts is
worse than no gate. So the uncovered surface is written down first, item by item, with the reason
each item is uncovered and whether it is reachable at all.

**One item on this list is not a gap but a defect.** The level filtering does not work: a message
logged below the configured level is still emitted, because `emit()` never asks the logger whether
the statement should be logged and the backend filters against the sink's threshold, which stays at
its default. The chain is in
[quill-runtime-formatting.md](quill-runtime-formatting.md). The test that would have caught it -
"a message below the configured level is not emitted" - has to be written as part of the coverage
work, and it will fail until the defect is fixed.

The three test files' worth of behaviour today is small. `tests/logging_test.cpp` has eight tests
and exercises: `set_level` / `current_level`, the ordering of the levels, `setup`, `flush`,
`info`, `warning`, `error`, `log_raw`, the integer / negative integer / boolean / character /
double / string-literal argument kinds, the indexed field, the escaped braces, and the source
location of a formatted and a raw call.

## 1. `modules/logging/format.hpp` - the module's private formatter

### 1.1 Branches that a test can reach

| What | Line | What a test would do |
|---|---|---|
| `message_buffer::append_padded`, the "left" alignment | `format.hpp:192-197` | log a value with a width, e.g. `"{:10}"` |
| `message_buffer::append_padded`, the "right" alignment (`>`) | `format.hpp:178-182` | log `"{:>10}"` |
| `message_buffer::append_padded`, the "centre" alignment (`^`) | `format.hpp:183-191` | log `"{:^10}"` |
| the buffer truncation at 2048 bytes | `format.hpp:159-161`, `:165-167` | log a string longer than 2048 bytes |
| `copy_text`, the precision branch | `format.hpp:302-304` | log `"{:.3}"` of a string |
| `copy_text`, the capacity branch | `format.hpp:305-307` | log a string longer than the 1024-byte per-argument buffer |
| `digit_char`, the uppercase table | `format.hpp:325-326` | log `"{:X}"` |
| `format_integer`, base 16 / 16-upper / 8 / 2 | `format.hpp:333-352` | log `"{:x}"`, `"{:X}"`, `"{:o}"`, `"{:b}"` |
| `format_integer`, the `+` and space signs | `format.hpp:368-372` | log `"{:+}"` and `"{: }"` |
| `format_integer`, the `#` alternate form | `format.hpp:373-383` | log `"{:#x}"`, `"{:#o}"`, `"{:#b}"` |
| `format_integer`, the zero padding | `format.hpp:395-398`, `:407-409` | log `"{:08}"` |
| `format_integer`, the truncation at the capacity | `format.hpp:399-401` | log a very wide integer |
| `format_value`, the `char const *` / `char *` branch | `format.hpp:434-436` | log a `char const *` **variable** - a string *literal* takes the array branch instead |
| `format_value`, the `string_like` branch | `format.hpp:451-454` | log a `std::string` or a `std::string_view` |
| `format_value`, the `self_formatting` branch | `format.hpp:455-457` | log a type with a `format_to(buffer, capacity)` member - **the project has no such type and no test for it** |
| `parse_spec`, every specification | `format.hpp:477-514` | log `"{:*>8+#.3x}"` and every single-character case |
| `format_message`, the `{:spec}` field | `format.hpp:563-569` | log any specification |
| `format_message`, the `char const *` branch | `format.hpp:434-436` | see above |
| `format_message`, an argument index beyond the argument list | `format.hpp:579` | **unreachable by construction** - `format_matches` rejects it at compile time |

### 1.2 Branches that no test can reach

| What | Line | Why | What to do |
|---|---|---|---|
| `scan_format` and `format_matches` | `format.hpp:220-294` | they are `consteval`: they run at compile time, so they produce no runtime arcs | a reviewed coverage exclusion, **or** the open question about whether GCC records them at all |
| the `volatile` and `const volatile` specialisations of `remove_cv` | `format.hpp:38-42` | nothing in the project has a volatile-qualified type | harmless - a type-only template produces no code |
| `remove_extent<T[]>` and `is_array<T[]>` | `format.hpp:64-66`, `:71` | no unbounded array is ever passed | harmless |
| the `is_integral` specialisations for `signed char`, `unsigned char`, `wchar_t`, `char16_t`, `char32_t`, `short`, `unsigned short`, `unsigned int`, `long`, `unsigned long`, `long long`, `unsigned long long` | `format.hpp:86-98` | the tests log `int`, `bool` and `char` only | each one is a separate `if constexpr` branch of `format_value`; they need a test each, or one test that logs one value of each width and signedness |
| `is_floating_point` for `float` and `long double` | `format.hpp:101-103` | only `double` is logged | two more tests |
| the `static_assert` in the `else` branch of `format_value` | `format.hpp:459-461` | it is a compile-time error, not a runtime path | no coverage needed, but it is the one place where a wrong argument type produces a diagnostic - and there is no negative-compile test for it |

## 2. `src/logging/quill_logger.cpp` - the implementation behind the standard-library-free boundary

| What | Line | What a test would do |
|---|---|---|
| `to_quill_level`, the `trace` / `debug` / `critical` cases | `quill_logger.cpp:39-51` | log at `trace`, `debug` and `critical` |
| `to_quill_level`, the `default` case | `quill_logger.cpp:51-54` | an out-of-range level - **not reachable through the module's `level` enum**, so it needs a direct call or an exclusion |
| `from_quill_level`, the `TraceL3` / `TraceL1` / `Notice` cases | `quill_logger.cpp:59-65` | quill's own levels, which the module never sets |
| `from_quill_level`, the `Backtrace` / `None` cases | `quill_logger.cpp:74-76` | ditto |
| `format_double`, the `capacity == 0` case | `quill_logger.cpp:123-125` | a zero-capacity call - **unreachable through the module**, which always passes 1024 |
| `format_double`, the `'f'` type | `quill_logger.cpp:131-137` | log `"{:f}"` - and this is where the **divergence** is |
| `format_double`, the `'e'`, `'E'`, `'G'`, `'g'` types | `quill_logger.cpp:138-154` | log `"{:e}"`, `"{:E}"`, `"{:G}"`, `"{:g}"` |
| `format_double`, the explicit-precision branches | `quill_logger.cpp:135`, `:139`, `:143`, `:152` | log `"{:.2f}"` and friends |
| `format_double`, the `written < 0` case | `quill_logger.cpp:157-160` | a failing `snprintf` - hard to trigger on purpose |
| `format_double`, the truncation at the capacity | `quill_logger.cpp:162-165` | a double whose text is longer than 1024 bytes - reachable with a large precision |

### 2.1 The `{:f}` divergence, which a test would expose

`format_double` treats `'f'` and the default type identically:

```cpp
case 'f':
case '\0':
  written = precision >= 0 ? std::snprintf(out, capacity, "%.*f", precision, value)
                           : std::snprintf(out, capacity, "%g", value);
```

With no precision it uses `%g`, the shortest representation. `std::format("{:f}", 3.5)` gives
`3.500000` - six digits after the point, as `std::format`'s default precision for `'f'`. The
project gives `3.5`. This is a specification deviation, it is currently untested, and it is the
cheapest defect in the project to fix or to pin down with a test.

## 3. The cib path - `include/cpp-core/logging/cib_quill.hpp`

**Nothing in the cib path is covered by the test suite, and nothing can be.** The tests link
`cpp-core::logging` and `cpp-core-catalog`, but not `cpp-core-app`, and the cib path's
instantiations live in `src/app.cpp`. So:

| What | Line |
|---|---|
| `level_of`, the `.value` branch and the plain branch | `cib_quill.hpp:45-51` |
| `decay_enum_value`, the `format_as` / non-enum branch and the `stdx::to_underlying` branch | `cib_quill.hpp:55-61` |
| `to_quill_level`, all eight cib levels | `cib_quill.hpp:68-88` |
| `quill_config::logger::log`, the whole callback | `cib_quill.hpp:129-161` |

**This is a scope decision that has to be made explicitly**, not a gap to be closed:

- **Option A** - the coverage denominator is the logging library and the module only. The cib path
  is excluded with a written reason ("it is the application adapter; the application is not under
  test"). Honest, but it leaves the level mapping untested.
- **Option B** - the test suite links `cpp-core-app` and a test drives the cib path, which makes
  the catalog IDs and the level mapping reachable and testable. More work, and the catalog
  tooling's `nm` scan has to be checked against the test binary.
- **Option C** - the level mapping is factored out of the header into something both paths share
  and that the test can call directly. This is the same refactoring the audit's table lists as
  "shrink" for row 11.

## 4. The application - `src/app.cpp` and `src/reflection_demo.cpp`

`demo::run()` (which calls `reflection_demo()`) is never called by the test suite; the
application is a separate executable that `ctest` does not run. The same scope decision as above
applies: either the application is outside the coverage denominator, or the test suite has to
exercise it.

## 5. The summary, in one table

| Area | Reachable by a test | Unreachable by construction | Out of scope by decision |
|---|---|---|---|
| `format.hpp` | the format specifications, the alignments, the truncations, the integer bases, the signs, the alternate forms, the zero padding, the `string_like` and `self_formatting` branches, the narrow integer types | the `consteval` scanner, the `volatile` type traits, the final `static_assert` | - |
| `quill_logger.cpp` | the three untested levels, the float types, the explicit precisions | the `default` level cases, the zero capacity, the failing `snprintf` | - |
| `cib_quill.hpp` | - | - | the whole path, unless the test suite links the application |
| `src/app.cpp`, `src/reflection_demo.cpp` | - | - | the application, unless the test suite runs it |

**The honest baseline is not close to 100%.** On the estimate above, roughly a third of the
runtime branches of `format.hpp` and most of `quill_logger.cpp` are unexercised. The work to close
the gap is mostly mechanical: a table-driven test that logs one value per format specification and
compares the output, and three more tests for the untested levels.

**The first measurement will correct this document.** Until the gate runs, every number here is a
prediction.
