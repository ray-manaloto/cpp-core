# What the tests do not reach

**Date:** 2026-11-11, updated 2026-11-13
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

**What this part now says, and why it changed.** Part 20 read the test file line by line, and the
finding changed the shape of the plan: **four of the eight tests assert `expect(true)`**. The
original table said what a test would *log*; a test that logs and asserts nothing is not a test,
it is a smoke test with extra steps. So every row below now says what the test must **assert** -
the exact output it must produce - and there is a table of the eight existing tests, what they
assert today, and what they must assert instead.

**The rule the assertions follow.** A test asserts a **value**, never a fact about the code. "The
logger did not throw" is not an assertion about the library; "the message says `a=1, b=2`" is. A
test that can only fail by crashing is not a test.

## 0. The eight tests that exist

| Test | Line | What it asserts today | What it must assert |
|---|---|---|---|
| "the level can be set and read back" | `logging_test.cpp:74-81` | that `set_level` and `current_level` agree | **that a message below the threshold is not emitted** - the assertion `DEF-1` needs. The round-trip is already asserted |
| "the levels are ordered from the least to the most severe" | `logging_test.cpp:83-90` | the order of the enum's values | that the order is the one the *sink* uses - `trace` to `TraceL2`, `critical` to `Critical` (`quill_logger.cpp:37-55`). The enum's order is not the mapping's order |
| "logging a message does not throw" | `logging_test.cpp:92-98` | `expect(true)` | the **text** of the message: `The answer is 42` |
| "a message can be logged with every kind of value" | `logging_test.cpp:100-112` | `expect(true)` | the text of each of the eight messages - `an integer: 42`, `a negative integer: -42`, `a boolean: true`, `a character: x`, `a double: 3.5`, `a string: hello`, `several values: 1 and 2 and 3`, `an indexed value: second and first`, `an escaped brace: {}`. **This one test is the whole format-dialect checklist** |
| "a message that is already formatted can be logged" | `logging_test.cpp:114-118` | `expect(true)` | that the raw message reaches the sink unchanged - `raw message` |
| "the format string is checked at compile time" | `logging_test.cpp:120-125` | `expect(true)` | that the well-formed call produces `1 of 2`. The **negative** cases (`{:s}` on an `int`) cannot be asserted at run time at all - they need the compile-failure harness, which is `FMT-15` |
| "a formatted log call carries the source location of the call" | `logging_test.cpp:127-142` | that the output contains `logging_test.cpp:<line>` | already right. Add: that the output does **not** contain the module's own line |
| "a raw log call carries the source location of the call" | `logging_test.cpp:144-159` | that the output contains `logging_test.cpp:<line>` | already right. Add: the same negative assertion |

**What the capture gives the tests.** `stdout_capture` (`logging_test.cpp:26-69`) redirects the
**file descriptor** of stdout to a temporary file and restores it in its destructor, so a test
that fails an assertion still puts stdout back. The framework prints its summary at the very end,
after every test has run, so nothing is lost. **Every assertion about a message's text needs this
capture** - there is no other way to see what was logged. The capture reads up to 4095 bytes
(`logging_test.cpp:61-63`), so a test that logs more than that must either use a shorter message
or read the file in pieces.

## 1. `modules/logging/format.hpp` - the module's private formatter

### 1.1 Branches that a test can reach

| What | Line | What the test must assert |
|---|---|---|
| `message_buffer::append_padded`, the "left" alignment | `format.hpp:192-197` | `"{:10}"` of `42` gives `42` and **eight** spaces after it |
| `message_buffer::append_padded`, the "right" alignment (`>`) | `format.hpp:178-182` | `"{:>10}"` of `42` gives **eight** spaces and then `42` |
| `message_buffer::append_padded`, the "centre" alignment (`^`) | `format.hpp:183-191` | `"{:^10}"` of `42` gives four spaces, `42`, four spaces - ⌊n/2⌋ before and ⌈n/2⌉ after |
| the buffer truncation at 2048 bytes | `format.hpp:159-161`, `:165-167` | a message longer than 2048 bytes comes out at **exactly** 2048 bytes, and is the prefix of the input |
| `copy_text`, the precision branch | `format.hpp:302-304` | `"{:.3}"` of `abcdef` gives `abc` |
| `copy_text`, the capacity branch | `format.hpp:305-307` | an argument longer than 1024 bytes is cut at **1024** bytes, and the message continues after it |
| `digit_char`, the uppercase table | `format.hpp:325-326` | `"{:X}"` of `255` gives `FF` - and not `ff` |
| `format_integer`, base 16 / 16-upper / 8 / 2 | `format.hpp:333-352` | `"{:x}"`, `"{:X}"`, `"{:o}"`, `"{:b}"` of `255` give `ff`, `FF`, `377`, `11111111` |
| `format_integer`, the `+` and space signs | `format.hpp:368-372` | `"{:+}"` of `42` gives `+42`; `"{: }"` gives `42` - one space, not a plus |
| `format_integer`, the `#` alternate form | `format.hpp:373-383` | `"{:#x}"`, `"{:#o}"`, `"{:#b}"` of `255` give `0xff`, `0377`, `0b11111111` |
| `format_integer`, the zero padding | `format.hpp:395-398`, `:407-409` | `"{:08}"` of `42` gives `00000042` - and `"{:08}"` of `-42` gives `-0000042`, the sign **before** the zeros |
| **the truncation at the capacity** | `format.hpp:399-401` | **corrected by part 20: this branch does nothing.** `total` is clamped and never read again; the real bound is the `at < capacity` guards at `format.hpp:404`, `:407`, `:410`. The test to write is "an integer wider than the 1024-byte argument buffer" → assert the message is cut at 1024 bytes and does not overrun |
| `format_value`, the `char const *` / `char *` branch | `format.hpp:434-436` | a `char const *` **variable** holding `hello` gives `hello` - a string *literal* takes the array branch instead |
| `format_value`, the `string_like` branch | `format.hpp:451-454` | a `std::string` and a `std::string_view` holding the same text give the same output |
| `format_value`, the `self_formatting` branch | `format.hpp:455-457` | **the project has no such type and no test for it.** The test has to define one - a type with a `constexpr format_to(buffer, capacity)` member - and assert the text it wrote. This is the only way that branch is ever executed |
| `parse_spec`, every specification | `format.hpp:477-514` | `"{:*>8+#.3x}"` gives its exact rendering, and every single-character case (`<`, `>`, `^`, `+`, `-`, `#`, `0`) gives its own exact output |
| `format_message`, the `{:spec}` field | `format.hpp:563-569` | any specification produces the specified output - the rows above, together |
| `format_message`, the `char const *` branch | `format.hpp:434-436` | see above |
| `format_message`, an argument index beyond the argument list | `format.hpp:579` | **unreachable by construction** - `format_matches` rejects it at compile time |

### 1.2 Branches that no test can reach

| What | Line | Why | What to do |
|---|---|---|---|
| `scan_format` and `format_matches` | `format.hpp:220-294` | they are `consteval`: they run at compile time, so they produce no runtime arcs | a reviewed coverage exclusion, **or** the open question about whether GCC records them at all |
| the `volatile` and `const volatile` specialisations of `remove_cv` | `format.hpp:38-42` | nothing in the project has a volatile-qualified type | harmless - a type-only template produces no code |
| `remove_extent<T[]>` and `is_array<T[]>` | `format.hpp:64-66`, `:71` | no unbounded array is ever passed | harmless |
| the `is_integral` specialisations for `signed char`, `unsigned char`, `wchar_t`, `char16_t`, `char32_t`, `short`, `unsigned short`, `unsigned int`, `long`, `unsigned long`, `long long`, `unsigned long long` | `format.hpp:86-98` | the tests log `int`, `bool` and `char` only | each one is a separate `if constexpr` branch of `format_value`; they need a test each, or one test that logs one value of each width and signedness - **and each has to assert its exact text**, because the branch is the type dispatch, not the rendering |
| `is_floating_point` for `float` and `long double` | `format.hpp:101-103` | only `double` is logged | two more tests, each asserting its exact text - and note that `float` and `long double` both go through `static_cast<double>` (`format.hpp:450`), so the assertion is about the **double** rendering |
| the `static_assert` in the `else` branch of `format_value` | `format.hpp:459-461` | it is a compile-time error, not a runtime path | no coverage needed, but it is the one place where a wrong argument type produces a diagnostic - and there is no negative-compile test for it |

## 2. `src/logging/quill_logger.cpp` - the implementation behind the standard-library-free boundary

| What | Line | What the test must assert |
|---|---|---|
| `to_quill_level`, the `trace` / `debug` / `critical` cases | `quill_logger.cpp:39-51` | a message at each of the three levels reaches the sink **with that level** - the pattern prints `LOG_%(log_level:<9)`, so the output says `LOG_TRACE`, `LOG_DEBUG`, `LOG_CRITICAL` |
| `to_quill_level`, the `default` case | `quill_logger.cpp:51-54` | an out-of-range level - **not reachable through the module's `level` enum**, so it needs a direct call or an exclusion |
| `from_quill_level`, the `TraceL3` / `TraceL1` / `Notice` cases | `quill_logger.cpp:59-65` | quill's own levels, which the module never sets |
| `from_quill_level`, the `Backtrace` / `None` cases | `quill_logger.cpp:74-76` | ditto |
| `format_double`, the `capacity == 0` case | `quill_logger.cpp:123-125` | a zero-capacity call - **unreachable through the module**, which always passes 1024 |
| `format_double`, the `'f'` type | `quill_logger.cpp:131-137` | `"{:f}"` of `3.5` gives **`3.500000`** - and this is where the **divergence** is. The test has to pin one of the two answers, and it is the defect `DEF-2` |
| `format_double`, the `'e'`, `'E'`, `'G'`, `'g'` types | `quill_logger.cpp:138-154` | `"{:e}"`, `"{:E}"`, `"{:G}"`, `"{:g}"` each give their exact text |
| `format_double`, the explicit-precision branches | `quill_logger.cpp:135`, `:139`, `:143`, `:152` | `"{:.2f}"` of `3.14159` gives `3.14` |
| `format_double`, the `written < 0` case | `quill_logger.cpp:157-160` | a failing `snprintf` - hard to trigger on purpose |
| `format_double`, the truncation at the capacity | `quill_logger.cpp:162-165` | a double whose text is longer than 1024 bytes - reachable with a large precision - gives **1023** bytes and a terminator |

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

| What | Line | What the test must assert |
|---|---|---|
| `level_of`, the `.value` branch and the plain branch | `cib_quill.hpp:45-51` | the level that comes back is the one that was asked for - and, for the mapping as a whole, **the quill level it becomes** (`DEF-7`) |
| `decay_enum_value`, the `format_as` / non-enum branch and the `stdx::to_underlying` branch | `cib_quill.hpp:55-61` | a scoped enum logs as its underlying integer, and a type with `format_as` logs as itself |
| `to_quill_level`, all eight cib levels | `cib_quill.hpp:68-88` | **the mapping itself, level by level** - and this is the test `DEF-7` needs: `MAX` must not become the least severe quill level, and `TRACE` must not become a more severe one than `USER2` |
| `quill_config::logger::log`, the whole callback | `cib_quill.hpp:129-161` | the message's **text** comes out as the catalog's text - with the compile-time argument folded in - and the **tags** carry the catalog ID and the module ID: `cpp_core id=<n> mod=<n>` (`cib_quill.hpp:146-148`) |

**This is a scope decision that has to be made explicitly**, not a gap to be closed:

- **Option A** - the coverage denominator is the logging library and the module only. The cib path
  is excluded with a written reason ("it is the application adapter; the application is not under
  test"). Honest, but it leaves the level mapping untested - and the level mapping is where
  `DEF-7` lives.
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

If it does, the assertions are: the three catalog messages come out with their exact text
(`src/app.cpp:27-30`), and the reflection demo's message says `cpp-core: C++26 static reflection OK
(point has 2 data members)` (`src/reflection_demo.cpp:27-28`).

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

**And the four `expect(true)` tests are the cheapest of them all.** Turning them into assertions
needs no new branch, no new type and no new fixture - only the expected text, which this part
now gives. That is the first thing to do when the lane reopens, and it moves the measured number
more than any other single change.

**The first measurement will correct this document.** Until the gate runs, every number here is a
prediction.
