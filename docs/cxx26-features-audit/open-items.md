# The open items and known issues

**Date:** 2026-11-11, updated 2026-11-12
**Status:** the single list of everything the audit could not settle, plus every defect and to-do it
found. Each item says what settles it and where it came from.

**Everything in this list needs a compile, a run, or an owner decision.** The build lane is parked,
so none of it has been applied. The items are ordered by the plan they belong to, and the plan
itself is in [README.md](README.md) and [PARKED.md](../../PARKED.md).

Two kinds of item are mixed here on purpose:

- **issues** - something is wrong today and should be fixed (section 1);
- **open questions** - something is not known yet and needs a measurement (sections 2 to 11).

Section 12 is the other way round: the questions that have **already** been answered, recorded so
that nobody re-derives them. Section 13 holds the ones that **carry an ID** and are answered or
contingent, so that a reference to `VCPKG-1` resolves to something.

**This file is the source of the machine-readable registry.** `scripts/audit_index.py` parses it
into `audit-index.json`, and `scripts/verify_audit.py` checks that the committed registry is up to
date. Never edit the JSON by hand - run `mise run audit:index`.

## 1. The issues - known defects, to fix

### DEF-1 - `set_level()` filters nothing on the module path

**A message logged below the configured level is still emitted.** This is a bug, not a trade-off.

The chain, read from the installed quill 13.1.0 headers:

| Step | Where | What |
|---|---|---|
| `set_level()` writes | `quill/core/LoggerBase.h:142-150` | the threshold into the **logger**'s `_log_level` |
| the only reader | `quill/core/LoggerBase.h:178, 188` | `should_log_statement` |
| quill's own wrappers call it | `LogMacros.h:404`, `LogFunctions.h:75` | so quill's own paths filter correctly |
| **cpp-core's `emit()` does not** | `src/logging/quill_logger.cpp:117` | calls `log_statement_runtime_metadata` directly |
| **the cib path does not** | `include/cpp-core/logging/cib_quill.hpp:157` | same |
| the backend filters against | `quill/backend/BackendWorker.h:1500` | each **sink**'s threshold, whose default is `TraceL3` (`quill/sinks/Sink.h:279`) |

**The fix:** three lines at each of the two call sites, copying `quill::detail::log`
(`quill/LogFunctions.h:63-83`).

**The test it needs:** "a message below the configured level is not emitted". The suite does not have
it, and it would fail today. It belongs with the coverage work.

### DEF-2 - the `{:f}` divergence

`format_double` (`src/logging/quill_logger.cpp:121-167`) treats the `'f'` type and the default type
alike and uses `%g`. So `{:f}` renders `3.5`, where `std::format` (and fmt) render `3.500000`.

**The fix:** use fmt in `format_double` (step 5 of the plan) - its default floating-point
presentation is the shortest round-trip, and `'f'` gives six digits after the point, exactly as
`std::format` does. Until then, a test should pin whichever behaviour is chosen.

### DEF-3 - the repository's comment overstates the standard

`modules/logging/logging.cppm:9-19` and `include/cpp-core/logging/internal.hpp:4-8` both say that "a
module's global module fragment is copied into every importing translation unit". That describes the
observed GCC and Clang failure accurately, but it is **not what the standard says**:

- [module.global.frag]/1: the global module fragment "can be used to provide declarations that are
  attached to the global module and usable within the module unit";
- [std.modules]/4-5: conforming implementations ensure that mixing `#include` and `import` does not
  result in conflicting attachments, and a declaration in the standard library denotes the same
  entity however it was made reachable.

So the GCC 16 failures are **implementation deficiencies, not ill-formed programs**, and the comment
should be corrected. The design conclusion does not change - and is arguably stronger, because a
deficiency is something the project works around until it is fixed upstream, whereas a rule
violation would be the project's own fault.

**The fix:** reword both comments. A comment-only change; no compile needed to know it is right.

**Also:** the same claim is in the root `README.md`, and it was in **three** places there:

1. at the top ("The logging module's interface is deliberately free of the standard library, because
   a module's global module fragment is copied into every translation unit that imports it");
2. in the Logging section ("A module's global module fragment is copied into every translation unit
   that imports it, so a standard header that the interface depends on ends up next to the standard
   headers of any translation unit that includes them");
3. in the Logging section's macro paragraph ("the module cannot include a header that its importers
   include, because the global module fragment is copied into every importer and the two copies of
   the header would collide").

**The README was corrected** when part 13 was written - which caught the first two and **missed the
third**. Part 16's line-by-line pass found the third and corrected it as well, so **the README is
now correct in all three places**; the two **source** comments are still to do, because they are
source changes and the build lane is parked.

### DEF-4 - the two logging paths do not share a format-string dialect

**The same format string produces different output depending on which path it goes through.** This
is new in part 13, and it is the most user-visible thing in this list.

| Call | The module path | The catalog path |
|---|---|---|
| `info("{:>06}", 42)` | "000042" | "    42" |
| `info("{}", 1234567.0)` | "1.23457e+06" | "1234567" |

The module path formats with the module's own scanner (`modules/logging/format.hpp`); the catalog
path formats with quill's bundled fmt, which implements the C++26 format-spec grammar and checks it
against the argument's type. Part 13 lists fifteen differences (D1-D15), of which these two are the
most consequential: the module's `0`-padding ignores the standard's "no zero padding when an
alignment is given" rule, and its default floating-point presentation is `%g` - six significant
digits - where the standard's is the shortest round-trip.

**The fix has three parts, and only one of them is small:**

1. the float default, in the implementation translation unit - this is **DEF-2** and step 5 of the
   plan (fmt in `format_double`);
2. the format-specification validation, in the module interface - this is **DEF-5**;
3. the dialect itself, which cannot be made identical while the module formats inside its own
   interface - this is **FMT-14**.

**The test it needs:** a differential test that formats the same values through both paths and
compares them. Part 13's D-table is the checklist.

### DEF-5 - the module never validates the format specification

**A format specification that `std::format` and fmt reject at compile time is accepted here, and
silently ignored at run time.** `scan_format` (`format.hpp:220-281`) scans the specification only to
find its end (`format.hpp:244-250`), and `parse_spec` (`format.hpp:477-514`) takes *any* trailing
character as the type character (`format.hpp:511-513`). So `info("{:s}", 42)` compiles, prints "42",
and tells the reader nothing.

**The fix:** the check would have to move from `format_matches<arg_count>` (`format.hpp:284-294`),
which knows only the *number* of arguments, into `format_string`'s constructor
(`logging.cppm:66-76`), which knows their *types*. That is a real piece of work - the scanner would
have to become a parser that is told the argument's type - and it is **FMT-14**'s option (b).

**The test it needs:** the negative compile-time cases - `{:s}` on an `int`, `{:d}` on a `double`,
`{:d.3}` on an `int`, `{:0}` on a string - each of which must stop compiling.

### DEF-6 - the catalog IDs are renumbered on every regeneration

**The same message does not keep its ID between releases.** The catalog's IDs are its wire
identifiers - the XML is MIPI Sys-T deployment collateral, and the `ID` attributes are what a
consumer decodes against - so an ID that moves is a wire format that changed.

**The cause.** The tool assigns the ID as the message's **rank among the messages, in text order**
(`gen_str_catalog.py:300-304`, `:228-229`): the messages are sorted by their text and the free
integers are handed out in that order. So a new message whose text sorts first takes ID 0 and
every existing message shifts up by one.

**Why it happens here.** The tool has a mechanism for exactly this, and the build does not use it.
`gen_str_catalog()` takes a `STABLE_JSON` argument (`string_catalog.cmake:16`), passes it as
`--stable_json` (`:85`), and the tool then keeps the ID of every message that already had one
(`gen_str_catalog.py:307-337`) and re-emits the old entries in the output JSON (`:465-472`), so the
JSON is its own stable file. `cmake/catalog.cmake` passes no `STABLE_JSON`, so the flag reaches
argparse with an empty list (`--stable_json` is declared `nargs="*"`, `gen_str_catalog.py:707-713`),
`read_stable([])` returns nothing, and **every regeneration renumbers from scratch**.

**What it is *not*.** It is **not** a cross-compiler problem: the IDs are stable across the two
compilers, and structurally so - the ID is a function of the message text, and the text is carried
in the message's *type*, which both compilers spell the same way. All nine catalogs on disk (two
compilers, four configurations, two build times) are byte-identical. Part 15 has the evidence and
the mechanism.

**The fix:** one line in `cmake/catalog.cmake` - pass the previous catalog as `STABLE_JSON`. Where
that file lives is an owner decision, and it is **BUILD-7**.

**The test it needs:** regenerate the catalog with one message added and check that the other
messages keep their IDs.

### DEF-7 - the catalog path's level mapping is inverted at both ends

**cib's most severe level is mapped onto quill's least severe one, and cib's least severe level
is mapped onto quill's second-least severe one.** This is new in part 20, and it is found by
reading the mapping against the two scales it claims to relate.

The mapping is at `include/cpp-core/logging/cib_quill.hpp:68-88`. The two scales run in opposite
directions:

| | The scale | Where |
|---|---|---|
| cib | `MAX = 0` (most severe) … `TRACE = 7` (least severe) | `log/level.hpp:8-17` |
| quill | `TraceL3` (least severe) … `Critical` (most severe) | `quill/core/LogLevel.h:26-44` |

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

The comment above the mapping (`cib_quill.hpp:63-67`) says the mapping "preserves the relative
order", and prints the two scales side by side as `TrL3 Crit Error Warn Info Debug TrL1 TrL2` -
which treats `TrL3` as quill's most severe level. Quill says the opposite: "TraceL3 is the most
detailed trace level", and `Critical` is the top of the scale (`quill/core/LogLevel.h:26-44`).

**What it costs.** The sink drops anything less severe than its threshold
(`quill/sinks/Sink.h:204`: `if (log_level < _log_level.load(...)) return false;`). With a sink at
`Error`, a `MAX` message is **dropped** and a `FATAL` message is **kept** - the exact opposite of
the intent. The two ends of the scale are swapped.

**Reachability.** `CIB_LOG_WITH_LEVEL(logging::level::MAX, ...)` reaches it
(`log/log.hpp:66-69`). The project never logs at `MAX` - the three catalog calls in
`src/app.cpp:27-30` are `CIB_INFO`, `CIB_WARN` and `CIB_ERROR` - so **nothing misbehaves today**.
It is a latent defect.

**Why it is not a one-line fix.** quill has exactly one level more severe than `Error`
(`Critical`), so eight cib levels cannot map one-to-one onto quill's ten; the mapping has to
decide which cib levels share a quill level, and the two ends are where it goes wrong. The fix
belongs with `DEF-1` - until the level filter works at all, the mapping's effect is not
observable - and with the level table in part 2.

**The test it needs:** a test that logs at each cib level and asserts the quill level it maps
to. The catalog path is not under test today (part 7, section 3), so this belongs with the
decision about the coverage denominator.

### DEF-8 - the formatter's section header names the wrong function

**`format.hpp:473` heads the wrong section.** The comment says "The formatter of a whole message",
but what follows is `parse_spec` - the function that parses one field's specification
(`format.hpp:477-514`). The function the header names, `format_message`, is 59 lines further down
(`format.hpp:532`).

This is new in part 20, and it is the smallest thing the reading found. Like `DEF-3`, it is a
comment defect: the code is right and the comment is wrong. Unlike `DEF-3`, nothing depends on it -
no diagnostic, no rule, no behaviour.

**Why it matters anyway.** These headers are the map of the file's structure, and this one names a
function that is 59 lines away. A reader who trusts it goes to `parse_spec` expecting the
whole-message formatter, and the file's two halves - the per-argument formatters and the
whole-message formatter - lose their boundary marker.

**The fix:** move the header down to `format_message`, or rename it to "The format specification".
A comment-only change; no compile needed to know it is right.

## 2. fmt and `constexpr` (FMT)

From [constexpr-and-fmt.md](constexpr-and-fmt.md) section 4.

| # | Question | Settled by |
|---|---|---|
| FMT-1 | Does `FMT_STATIC_FORMAT` compile on both toolchains? It needs `FMT_USE_NONTYPE_TEMPLATE_ARGS` and a `constexpr` `format_to`; both are C++20 features, so it should | a compile on `gcc16` and `p2996` |
| FMT-2 | Does fmt's compile-time formatting really handle **floating point** on both toolchains? P3391R2 §2.4 says fmt's implementation does; the compiler has to constant-evaluate it | a compile |
| FMT-3 | Does `FMT_STATIC_FORMAT` need a constexpr `std::string`? The source says no - it returns a `char[N]`-backed `static_format_result` - but the `fmt::format` overload does, and the two must not be confused | reading `fmt/compile.h:565-578` (done) plus a compile |
| FMT-4 | Can `format.hpp` be made `constexpr` wholesale, and does the compiler accept it? `message_buffer` is a 2,048-byte object and `format_message` takes the addresses of its arguments | a compile - **the compiler is the test** |
| FMT-5 | Does the `static_assert` test pattern work? Specifically: does `format_message` constant-evaluate when its arguments are `constexpr` objects of static storage duration, and fail cleanly when they are temporaries? The `values[]` array is the risk | a compile |
| FMT-6 | What does fmt produce for the project's float cases? The switch from `%g` (six significant digits) to fmt's shortest round-trip changes the output for `0.1`, `1.0/3.0`, `1e-7`, `1e20` and the infinities | a run |
| FMT-7 | Does fmt's `format_to_n` behave the same as `snprintf` for the truncation contract? The module truncates at 2,047 bytes silently; `format_to_n` returns `format_to_n_result{count, error_code}` and the error code has to be checked | a compile |
| FMT-8 | Can a custom `fmt::formatter<T>` be written for a project type, and does it interoperate with quill's `fmtquill`-based runtime formatter? If not, the two-copies problem needs a project rule about which namespace custom formatters use | a compile |
| FMT-10 | Does `std::source_location::current()` in a default argument on `quill_config::logger::log` return the **caller's** location, given that the call goes through the `logging::log<Env>` template? It may be the reason the CIB macro cannot be dropped | a compile - **also MAC-1** |
| FMT-11 | Does the catalog tooling's `nm` scan still find the same undefined `catalog<>` / `module<>` symbols if the cib tag string is built with `fmt::format`? The tags are runtime data, not types, so it should not matter | a run - **also MAC-2** |
| FMT-12 | Does `fmt::runtime` exist in fmt 12.2.1's public API under that name, and is it the right way to format a runtime-built specification in `format_double`? | reading the header, plus a compile |
| FMT-13 | What are the **authoritative** feature-test macro values on each toolchain? Part 11 reports *declaration* and the set of values each macro is declared with, because both libraries define their macros inside per-standard-version branches and a text scan cannot pick the right one. The authoritative answer needs the preprocessor - one `#include <version>` and a `static_assert` per macro | a compile |

| FMT-15 | **How are the four asymmetric divergences tested?** D1, D8, D9 and D14 are *compile-time rejections on one side only* - fmt rejects `{:s}` on an `int` and `{:d.3}` on an `int`, and the module rejects `"{:{}}"` and `"{0} {0}"`. A runtime differential test cannot compare two programs when one of them does not compile, so **these four need a "must not compile" mechanism**, and the project has none. CMake's `try_compile` returns a boolean but cannot `import com.rsm.logging;` (the module has to be built first, and the import path is CMake-internal). The workable route is a ctest fixture that reads the compile command out of `compile_commands.json` (already generated), substitutes the source and asserts that the compiler **fails**. These four are the most important cases - D1 is the difference between a checked and an unchecked format string - so a design that dropped them would drop the point | a build-system change, then a run |

**FMT-9 has moved to [section 13](#13-the-items-that-are-answered-or-contingent)** - part 18,
section 2 answered it by reading the upstream vcpkg port.

## 3. quill's runtime formatting (QUIL)

From [quill-runtime-formatting.md](quill-runtime-formatting.md).

| # | Question | Settled by |
|---|---|---|
| QUIL-1 | Does a `Codec` that pushes three arguments from one pack element satisfy a `"{} {} {}"` statement? **This is the load-bearing unknown for the whole formatter rewrite** | one scratch translation unit |
| QUIL-2 | Which types can be pushed into `DynamicFormatArgStore` without a formatter - `bool`, `char`, the signed and unsigned 8/16/32/64-bit integers, `float`, `double`, `long double`, `void const *`, `string_view`? And does a scoped `enum` push as its underlying integer, or does it need a formatter? (The cib path already has `decay_enum_value` at `cib_quill.hpp:55-61` for this reason) | a compile |
| QUIL-3 | Exactly which default-specification outputs change between the module's `snprintf("%g")` and fmt's shortest round-trip? | a run - **overlaps FMT-6** |
| QUIL-4 | Does fmt render the whole specification cross-product identically to the module's `parse_spec` - in particular `#` with `b`/`x`/`o`, `0` padding combined with a sign, `^` centring, and precision on a string (fmt truncates; the module clamps in `copy_text`, `format.hpp:477-514`)? | a compile and a differential test |
| QUIL-5 | Can the module's `format_string` hold a compile-time-rewritten template - a struct with a `char[N]` member and no standard-library types - so that the pre-formatted fields become `{}` and the pass-through fields keep their specification? This is what the `self_formatting` path needs | a compile |
| QUIL-6 | Will the compiler accept a `char const[N]` with no terminator at the `consteval format_string` boundary (`logging.cppm:67`)? If it will, option (b) introduces an out-of-bounds read in quill's `safe_strnlen` that is impossible today, and the consteval check would have to require `text[N-1] == '\0'` | a compile |
| QUIL-7 | Does a message over 2047 bytes behave acceptably on the default `UnboundedBlocking` queue, and would a bounded queue throw `QuillError` (`Logger.h:871-882`) where the message is silently truncated today? | a run |

## 4. The tooling (TOOL)

From [tooling-design.md](tooling-design.md) sections 3.6 and 5. Q1-Q7 in section 3.6 are the
coverage run; the rest are clang-tidy, cmake-format and the CI.

| # | Question | Settled by |
|---|---|---|
| TOOL-1 | Does the proposed `.clang-tidy` pass `clang-tidy --verify-config` on Homebrew 23.1.5, and does `clang-tidy -p <build> --config-file=.clang-tidy src/app.cpp` exit non-zero on any enabled-check warning with `WarningsAsErrors` enabled? Does it parse the p2996 `compile_commands.json` without the `-freflection` `RemovedArgs` hack, and with it? | a run |
| TOOL-2 | Can clang-tidy parse `modules/logging/logging.cppm` at all, standalone with `-x c++-module`? If yes, is the diagnostic output usable (do the enabled checks skip module declarations via `SkipDeclsInModules`, PR #145630 - and is that in 23.1.5)? The default stays "do not check the `.cppm`" until it is measured. **Part 18, section 8.2 answers the parenthetical by reading:** llvm#145630 **closed on 2026-03-19**, before the LLVM 23.1 series was cut on 2026-08-25, so `SkipDeclsInModules` **is** in 23.1.5. The measurement itself is still a run | a run |
| TOOL-3 | Can a BMI for `com.rsm.logging` produced by **Homebrew clang 23** be fed to clang-tidy via `-fmodule-file` / `-fprebuilt-module-path` for `src/main.cpp` and `tests/logging_test.cpp`? Probably not (p2996 flag and dialect mismatch), in which case they stay skipped. `src/reflection_demo.cpp` is impossible (`<meta>`) regardless | a run |
| TOOL-4 | Does `clang-tidy` on `src/app.cpp` parse cleanly with Homebrew clang 23 (`-std=c++26` + the removed reflection flags), or do the cib headers trip diagnostics or crashes? Maybe drop `clang-analyzer-*` if CSA asserts on cib's macro machinery | a run |
| TOOL-5 | What is the exact on-disk layout after `cmake --build --preset gcc16-coverage` - where do the `.gcno` / `.gcda` files of a `CXX_MODULES` member (`modules/logging/logging.cppm`) and of the `cpp-core-catalog` static library land? Does the codegen compile allow `-fprofile-arcs` unmodified? Does `-fprofile-abs-path` make `files[].file` absolute? | a run |
| TOOL-6 | Does GCC 16 emit instrumentation arcs - and zero-count arcs - for (a) uninstantiated templates in `logging.cppm` / `format.hpp`, (b) `consteval` functions (`scan_format`, `format_matches`, the `format_string` constructor body)? Which lines appear in gcov's JSON at all? **This decides whether the coverage numbers can be trusted at all** | a run |
| TOOL-7 | Is `unexecuted_block` set on lines counted as covered (count > 0 with some unexecuted blocks), and do we gate on it (strict) or not (line-only)? | a run |
| TOOL-8 | What is the **actual** uncovered-line list today? [coverage-gaps.md](coverage-gaps.md) and PARKED's list are a hypothesis to be confirmed or refuted. The gate then means: extend the tests until the list is empty, plus a small reviewed exclusion file with a justification per entry | a run |
| TOOL-9 | Does `ctest --preset gcc16-coverage` return non-zero on test failure, and does the workflow preset propagate it to the `coverage` target? Does the instrumented binary write `.gcda` atomically - counters are flushed at normal exit, so `std::quick_exit` or a signal would lose them (ut's main returns normally)? | a run |
| TOOL-10 | Does the catalog-generated file (`cpp-core-catalog.cpp`, in the build dir) need excluding explicitly, or does the build-dir exclusion suffice? And how do `cpp-core-test-code`'s `.gcno` files merge (same file `logging_test.cpp`, excluded by the `tests/` filter anyway)? | a run |
| TOOL-11 | Confirm that for lines instrumented in multiple translation units, "any count > 0 means covered" yields the same result as summing, and document that template lines common to several TUs are merged by union - so the repository total is the **union** of files | reading the gate script |
| TOOL-12 | Does branch coverage work: does `-b` produce usable `branches[]` in gcov-16's JSON for these TUs, and is the `-fcondition-coverage` bitset stable enough to gate on? Probably: no gate, advisory only | a run |
| TOOL-15 | Does `.clang-format` and `.cmake-format.yaml` agree on anything besides `line_width = 100`? (`tab_size`, `line_ending`, markup-off / reflow-off.) Cosmetic, but worth editing together | a run |
**TOOL-16 has moved to [section 13](#13-the-items-that-are-answered-or-contingent)** - it is not
a measurement. It asks what CI image would provide `gcov-16`, and the project has no CI at all
(`BUILD-5`), so the question is **contingent on `BUILD-5`'s answer**, not a run.

**Resolved since the design note was written:** the `.editorconfig` question (`indent_size = 3` should
become 2) - done in `2ef42de`.

## 5. `import std;` and the module boundary (MOD)

From [import-std.md](import-std.md).

| # | Question | Settled by |
|---|---|---|
| MOD-1 | How large is the GCC migration in option (c), exactly? Which of the importers' headers would have to become `import std;`, and does the POSIX include in the tests survive the mix? | a compile |
| MOD-2 | Can the type-erasure boundary of option (b) be made to work with a small, fixed-size representation - a function pointer table, a variant of primitives - and how much code would that be? | a compile |
| MOD-3 | Does GCC 16.2 translate an `#include` of an importable header **inside a module unit** (global module fragment or purview), and does it then diagnose the [cpp.import]/2 ill-formedness - or silently accept non-conforming code? | a compile |
| MOD-4 | Does GCC 16.2 reject an importing translation unit that includes **only** `<unistd.h>` (no C++ standard headers)? The measurement covers "any standard or system header"; the isolated case is untested | a compile |
| MOD-5 | Is `<unistd.h>` in GCC 16's importable-header set, so that [cpp.include]/10 translation could ever apply to it? | a compile |
| MOD-6 | Does the GCC 16.2 failure persist when `--compile-std-module` has actually built the `<bits/stdc++.h>` header unit - that is, is the failure an artefact of CMake not building header units, or a merge deficiency in GCC? | a compile |
| MOD-7 | Does CMake's dependency scanning handle `#if` around `import std;` in `logging.cppm`? | a run |
| MOD-8 | Do quill's, cib's and ut's headers compile in a translation unit that imports `std` on clang-p2996? libc++ documents include-after-import failures | a compile |
| MOD-9 | Does the catalog's `nm` scan still find the same undefined `catalog<>` / `module<>` symbols when the importers use `import std;`? | a run |
| MOD-10 | Does a translation unit that **imports** `com.rsm.logging` *and* **includes** `cpp-core/logging/cib_quill.hpp` compile on both compilers? No such translation unit exists today - the test file imports the module but not `cib_quill.hpp`, and `src/app.cpp` includes `cib_quill.hpp` but does not import the module - and `cib_quill.hpp` pulls in `<string>`, `<string_view>`, `<type_traits>`, `<cstdint>`, `<utility>`, quill's headers, cib's `<log/log.hpp>` and `<stdx/*>`. The audit's matrix says an importing TU that includes a standard header **fails** on GCC 16 (`import-std.md:206`), while the project's own test file does exactly that and builds, so the two cases differ in some way the audit did not isolate. **The differential test needs this to work** - if it does not, the test has to put the two paths in separate translation units | a compile |
| MOD-11 | **Does the GCC 16 matrix's failure reproduce in the project's actual configuration?** The audit's matrix was measured with **`-fmodules`** (`import-std.md:188`), but the project's GCC 16 compile commands use **`-fmodules-ts`** - CMake 4.4.5's `Modules/Compiler/GNU-CXX.cmake` sets `CMAKE_CXX_MODULE_MAP_FLAG` to `-fmodules-ts` for GCC >= 14, and `build/gcc16-debug/compile_commands.json` shows `-std=c++26 -freflection -fmodules-ts -fmodule-mapper=...`. **The project's own GCC 16 build does the shape the matrix says fails**: `tests/logging_test.cpp` imports the module and includes `<cstdio>`, `<string>` and `<unistd.h>`, the module exports no standard-library types, and `build/gcc16-debug/tests/cpp-core-tests` exists. So *"option (c) is blocked on GCC 16 today"* (`import-std.md:295`) is **not established for this project**. This is the one measurement that decides the price of option (c) | a compile |

**One question this section has already answered:** *should the test framework's module variant be
used?* **No** - it is reachable (upstream ships the `import std` gate table, and its CMake 4.4 UUID
is the one this project already uses) but not usable, because `import ut;` makes the `std` module
reachable in the test translation unit and GCC 16 then collides with the standard headers the test
file needs. Part 14 has the evidence; the answer does not depend on MOD-6's outcome.

## 6. Static reflection (REFL)

From [reflection.md](reflection.md) section 8.

| # | Question | Settled by |
|---|---|---|
| REFL-1 | Do clang-p2996's 1-argument `members_of` form and GCC's 2-argument form compile the **same** source, or is the incompatibility only in the standard-library wrapper? | a compile |
| REFL-2 | Are `std::meta::access::unprivileged()` (P1306R5) and `std::meta::access_context::unchecked()` (P2996R13, what the project uses) the same API under different names, or distinct? | a compile |
| REFL-3 | Does `std::meta::exception` throwing work reliably inside `consteval` reflection calls in both compilers, for diagnostics like cpp-core's "format string does not match"? | a compile |
| REFL-4 | When libstdc++ and libc++ implement P3391R2, does `std::format_string<Args...>` accept every format string the project's own scanner accepts? The two dialects are not identical - the hand-rolled scanner rejects named arguments and a bare `}` (`format.hpp:239-241, 270`), and `std::format_string` rejects a few things the scanner allows | a compile, once the libraries implement it |

**Already known, and the reason reflection changes nothing today:** GCC throws
`std::meta::exception` ("reflection with has_identifier false") for
`std::meta::identifier_of` on a plain type reflection (README question 6).

## 7. The macros (MAC)

From [macro-reduction.md](macro-reduction.md) section 7.

| # | Question | Settled by |
|---|---|---|
| MAC-1 | Does `std::source_location::current()` in a default argument on `quill_config::logger::log` return the **caller's** location? It should - the default argument is evaluated at the call site - but the call goes through `logging::log<Env>`, which is a template, so the "call site" is the `logging::log` invocation inside the macro, not the user's line. **This may be the reason the macro cannot be dropped** | a compile - **the same as FMT-10** |
| MAC-2 | Does the catalog tooling's `nm` scan still find the same undefined `catalog<>` / `module<>` symbols if the calls are written macro-free? The mangling of the specialisations is unaffected in theory | a run - **the same as FMT-11** |
| MAC-3 | Would `std::format_string<Args...>` accept the format strings the project uses today? The module's scanner rejects named arguments and a bare `}`; `std::format_string` rejects a few things the hand-rolled scanner accepts. The difference has to be enumerated before any switch | a compile - **the same as REFL-4** |

## 8. The coverage to-dos (COV)

Not questions - work items. The gate is not 100% today, and these are what closes the gap. From
[coverage-gaps.md](coverage-gaps.md), branch by branch.

| # | What is not reached | Where |
|---|---|---|
| COV-1 | `trace`, `debug` and `critical` - none of the three is called by any test | `logging.cppm:85-151` |
| COV-2 | The level-filtering branches, and the assertion that a message below the threshold is suppressed - **this is DEF-1's test** | `quill_logger.cpp:105-119` |
| COV-3 | Almost every format specification: alignment and fill, sign, `#`, zero padding, precision, `x`/`X`/`o`/`b`, uppercase digits, `^` centring | `format.hpp` |
| COV-4 | The 2,048-byte buffer truncation | `format.hpp:154-206` |
| COV-5 | The `self_formatting` path - no `self_formatting` type exists in the codebase today | `format.hpp:424-463` |
| COV-6 | The `is_array` and `string_like` branches | `format.hpp:70-72` |
| COV-7 | The cib/catalog path - `demo::run()` in `src/app.cpp` is never called by any test; the catalog IDs are produced but never executed | `src/app.cpp`, `cib_quill.hpp` |
| COV-8 | The internals of `quill_logger.cpp`: logger-creation races, the `current_level` getter's edge cases | `quill_logger.cpp` |
| COV-9 | `src/reflection_demo.cpp` is compiled, but its runtime line only runs if reflection works at runtime (it does) - and nothing calls it in the tests | `src/reflection_demo.cpp` |
| COV-10 | `log_raw`'s length path is only partially exercised | `logging.cppm:101-105` |

**The `constexpr` change removes half of this from the runtime-coverage problem.** With
`format.hpp` `constexpr`, every formatting rule becomes a `static_assert` that the compiler checks,
on **both** compilers, with no test binary and no coverage instrumentation. That is a stronger
guarantee than a runtime test, and it is exactly what a 100% coverage target wants: the
compile-time-only code the coverage report cannot see gets verified instead.

## 9. The build system (BUILD)

From [build-and-dependencies.md](build-and-dependencies.md). These are new: the features audit
never treated the build as a subject. **BUILD-6 is answered - see section 12.**

**All BUILD owner decisions (BUILD-1 through BUILD-9 except BUILD-6) have been answered and are recorded in [section 13](#13-the-items-that-are-answered-or-contingent).**

## 10. The dependency tree (VCPKG)

From [build-and-dependencies.md](build-and-dependencies.md).

**Both items below have moved to
[section 13](#13-the-items-that-are-answered-or-contingent)** - they were recorded as needing "a
reading of the registry at the pinned baseline", which was believed to be impossible because
`$VCPKG_ROOT` is the vcpkg *tool* with no `ports` tree and no `.git`. The registry is a git
repository and the baseline is a commit in it, so the reading is done over HTTP against that
commit, without a checkout. Part 18, section 2.

## 11. The environment (ENV)

| # | Item | Settled by |
|---|---|---|
| ENV-1 | The two copies of fmt: the standalone `fmt` 12.2.1 (namespace `fmt`) and quill's bundled `fmtquill` 12.2.0. **The project rule is that custom formatters are written for `fmt` only**; the cib path formats primitives and decays its one project type to its underlying integer | a decision now, revisited at FMT-9 |

**ENV-2 and ENV-3 have been answered and moved to [section 13](#13-the-items-that-are-answered-or-contingent).**

## 12. What is *not* an open question

These were asked, answered and are recorded so nobody re-derives them.

| Question | Answer | Evidence |
|---|---|---|
| Is `std::format` `constexpr` in C++26? | **Yes** - P3391R2, adopted at Kona in November 2025, `__cpp_lib_constexpr_format 202511L` | the C++26 draft's synopsis |
| Is it implemented here? | **No** - libstdc++ 16 and libc++ 21 both lack the macro; llvm#171292 is open | the installed headers |
| Does fmt format floats at compile time? | **Yes**, and it does not need a constexpr `std::string` - `FMT_STATIC_FORMAT` returns a `char[N]`-backed `static_format_result` | P3391R2 §2.4; `fmt/compile.h:565-578, 594` |
| Can `std::format` format floats at compile time? | **No** - only the integral overloads of `std::to_chars` are `constexpr` (P2291R3) | P3391R2 §2.1 |
| Can fmt enter the module interface? | **No** - a textual `#include` in a module unit yields global-module declarations, which collide with the importer's own standard headers. It would need `import std;` (clang-p2996 only) or a fmt module (there is none) | `fmt/base.h`'s include list; the observed GCC and Clang errors |
| Is the global module fragment "copied into every importing translation unit"? | **No** - that is the observed failure mode, not the rule. [module.global.frag]/1 and [std.modules]/4-5 | the C++26 text |
| Can Intel's `stdx` replace the hand-rolled scanner? | **No** - `stdx/ct_string.hpp:8-14` includes seven standard headers; `stdx/ct_format.hpp` adds `<algorithm>`, fmt and Boost.MP11 | the installed headers |
| Can static reflection replace anything today? | **No** - every range-returning metafunction allocates, and neither compiler implements constexpr allocation (P2680 / P1974) | the C++26 text |
| Should the `CIB_*` macros stay? | **Yes** - the mechanism underneath is already macro-free, and every macro has a macro-free equivalent, but each costs verbosity at the call site and buys nothing the project does not already have. Four invocations, all in `src/app.cpp` | [macro-reduction.md](macro-reduction.md) |
| Can clang-tidy check the module interface unit? | **No** - the co_compile invocations are unconsumable (llvm#62258) and the module's binary is locked to the clang that built it (llvm#63939). Check the non-module translation units only | the llvm issues |
| Which coverage route works here? | **GCC 16 + `gcov-16 --json-format` + a stdlib-only Python gate.** Clang's raw profile is v10 and `llvm-profdata` 23.1.5 wants v11; `gcovr` is broken on this machine; `lcov` and `genhtml` are absent | [tooling-design.md](tooling-design.md) |
| Is `std::inplace_vector` available on libc++ 21? | **No** - there is no `<inplace_vector>` at all, not merely a missing macro. The deferral in the audit's table stands. (A naive grep of libc++'s `<version>` says otherwise, because the file opens with a synopsis block that lists unimplemented features) | part 11 |
| Is `std::from_chars` for floating point an option? | **No** - neither library declares `__cpp_lib_from_chars`. `to_chars` for floats *is* available in both (libc++ has the overloads but did not bump its macro) | part 11 |
| Is `std::execution` (P2300) in libstdc++? | **No** - libstdc++'s `__cpp_lib_execution 201902L` is C++17's P0443 (parallel algorithms), and its `<execution>` contains no senders at all | part 11 |
| Is `std::simd` usable? | **No** - libstdc++ 16 ships a `<simd>` with no `std::simd` class in it; libc++ 21 has no `<simd>` | part 11 |
| Does declaring `"fmt"` in `vcpkg.json` cost anything? | **No** - fmt 12.2.1 is already installed, because `intel-cpp-std-extensions` depends on it. It is a one-line manifest change with no download and no port rebuild | part 12 |
| Are the two copies of fmt avoidable? | **No** - the vcpkg `quill` port installs only `quill/bundled/fmt/`, so quill's `fmtquill` and the standalone `fmt` coexist whatever the project does. The rule stands: custom formatters are written for `fmt` only | part 12 |
| Does the project have CI? | **No** - there is no `.github/` directory and no git remote. `TOOL-16`'s question about a CI image is moot; the gates are local presets until CI exists | part 12 |
| Does the project set compiler warnings? | **No** - there is not one `-Wall`/`-Wextra`/`-Wpedantic` in the toolchain or in any target. `BUILD-1` is the owner's decision | part 12 |
| Can another project consume cpp-core? | **Not today** - there is no `install()` call and no export set. `BUILD-2` and `BUILD-3` are the owner's decisions | part 12 |
| Does the module path share a format-string dialect with the catalog path? | **No** - and the differences are silent. Part 13 lists fifteen of them; the two that matter most are `{:>06}` (the module path gives "000042", fmt gives "    42") and the default float presentation (`%g`, so 1234567.0 prints as "1.23457e+06" where fmt gives "1234567"). This is **DEF-4** | part 13 |
| Is the module's format specification checked against the argument's type? | **No** - `scan_format` only finds the specification's end and `parse_spec` takes any trailing character as the type, so `{:s}` on an `int` compiles and is silently ignored. This is **DEF-5** | part 13 |
| Did Intel write a constexpr formatter of its own? | **No** - Intel's `stdx::ct_format` is fmt's compile-time API: `STDX_FMT_COMPILE` is `FMT_COMPILE` (`stdx/detail/fmt.hpp:14`), and `perform_format` is a `consteval` that calls `fmt::format_to` into a fixed-size `ct_string` (`stdx/ct_format.hpp:326-331`). Intel's *own* hand-rolled formatter is the freestanding one, and it `static_assert`s what it does not support. **The fmt decision is corroborated independently** | part 14; `upstream/stdx/` |
| Should the test framework's module variant be used? | **No** - it is *reachable* (upstream ships the `import std` gate table, and its CMake 4.4 UUID is the one this project already uses) but not *usable*: `import ut;` makes the `std` module reachable in the test translation unit, and GCC 16 then collides with every textual standard include - and `tests/logging_test.cpp` needs `<cstdio>`, `<string>` and `<unistd.h>` | part 14; `upstream/ut/` |
| Is the logger's lifetime sound? | **Yes**, with one hazard in the public API: the backend is stopped at exit through quill's own `atexit` handler, the level threshold is atomic, and the project's level round-trip is exact. The hazard is `flush()`, which quill says must not be called from a static object's destructor (`quill/Logger.h:613`) and which the project's public API does not mention - **QUIL-9** | part 14 |
| Is DEF-1 a data race? | **No** - the threshold is atomic (`quill/core/LoggerBase.h:224`) and correct; the module path simply never asks. The *sink* threshold (default `TraceL3`) is what filters, so everything is written. It is a policy defect, not a race | part 14 |
| Is fmt's constexpr support still pending? | **No** - fmt#3403 was **closed as completed** on 2023-06-17, and the installed 12.2.1 has it. The remaining blocker is the standard libraries' (llvm#171292, still open; and LWG4531, which settled the macro values at Brno in June 2026) | part 14 |
| Where does the module path format its message? | **On the calling thread**, and then it is copied into a `std::string` - so each module-path message costs one copy of its bytes on the calling thread, plus a heap allocation for any message longer than the small-string threshold (`logging.cppm:110-112`, `quill_logger.cpp:118`; the thresholds are in part 18, section 4). The catalog path queues the arguments and formats on the backend thread. The root README's "What the two paths share → Threading" said only the second | part 13; part 14; part 18 |
| Are the catalog IDs stable across compilers? | **Yes - and structurally, not by luck.** The ID is a function of the **message text** (the rank among the messages, in text order), and the text is carried in the message's *type* (`sc::string<char...>`), which both compilers spell the same way. All nine catalogs on disk - two compilers, four configurations, two build times - are byte-identical. The *link* is the backstop: a message that the tool dropped or misread leaves an undefined `catalog<...>` symbol | part 15 |
| Are the catalog IDs stable across *releases*? | **No** - and that is **DEF-6**. The ID is the rank in text order, so adding a message that sorts first renumbers every later one, and the build does not use the tool's `STABLE_JSON` mechanism that would prevent it. The XML is MIPI Sys-T deployment collateral, and the IDs are its wire identifiers | part 15 |
| Does the upstream vcpkg `quill` port have an opt-in feature for an external fmt? | **No.** At the pinned baseline the upstream `quill` port has **no `features` key at all** and depends only on `vcpkg-cmake` and `vcpkg-cmake-config`; its portfile passes no fmt option. quill 13.1.0's own CMakeLists has no fmt switch either - none of its 26 `option()` calls mentions fmt - and it installs `include/quill/bundled/fmt/*` unconditionally, exposing it as the `fmtquill` interface target. So **the two copies of fmt are structural**, and there is no such feature to opt into | part 18, section 2 |
| Do the five overlay ports shadow builtin vcpkg ports? | **No.** The baseline's tree was enumerated in full (17,869 paths, not truncated): none of `ut`, `intel-cib`, `intel-cpp-std-extensions`, `intel-baremetal-concurrency` or `intel-baremetal-senders-and-receivers` appears in `ports/` or in `versions/`. The nearest names the registry ships are `utf8-range`/`utf8h`/`utf8proc` and `intel-ipsec`/`intel-mkl`/`intelrdfpmathlib`. So all five **track upstream rather than the pinned baseline** - the opposite of the shadowing failure `ports/README.md` warns about | part 18, section 2 |
| Does the module path flush on every message? | **No, and it never did.** `<true>` means *"honour the per-logger immediate-flush threshold"* (`quill/Logger.h:945-952`), and the check returns immediately when the threshold is 0 (`Logger.h:995-999`). The threshold **is** 0 - it defaults to 0 (`quill/core/LoggerBase.h:221`) and the project never calls `set_immediate_flush()`. Quill's own default is the same value (`QUILL_ENABLE_IMMEDIATE_FLUSH 1`, `quill/LogMacros.h:131`), so the module path already matches quill's macro-free default. **QUIL-8** | part 18, section 4 |
| Does each module-path message cost one heap allocation? | **Only for messages longer than the small-string threshold** - 22 characters on libc++ 21 (`string:834`, `:896`), 15 on libstdc++ 16 (`bits/basic_string.h:217`). `emit()` constructs `std::string{message, length}` (`quill_logger.cpp:118`), so a shorter message never touches the heap. The bytes are still copied twice - into the small-string buffer, then into the queue. The root README's claim is therefore wrong for short messages | part 18, section 4 |
| Is MemorySanitizer available on this toolchain? | **No - two independent blockers.** GCC 16 does not implement MSan at all (there is no `memory` in its `-fsanitize=` list), and clang's MSan "is supported on the following OS: Linux NetBSD FreeBSD" - macOS is not among them. The installed libc++ 21 snapshot has no MSan support either: no `__msan` directory in the include tree and not one "MemorySanitizer" mention anywhere in it. So the preset table is complete as it stands, and the missing sanitizer is missing for a structural reason | part 18, section 7.2 |
| Can another project consume cpp-core's module? | **Not today, and the mechanics are now known.** There is no `install()` call and no export set, so no `find_package(cpp-core)` and no `import com.rsm.logging;` from outside. It is **doable**: `install(TARGETS cpp-core-logging EXPORT ... FILE_SET CXX_MODULES ...)` plus `install(EXPORT ... CXX_MODULES_DIRECTORY ...)` (CMake 3.28) - CMake's own words: "without this information, none of the C++ modules which are part of the targets in the export set will support being imported in consuming targets". Three project-specific obstacles: `format.hpp` is a `PRIVATE` source but a **public build-time dependency** of the installed module, `internal.hpp` is in the global module fragment and is not in a file set, and the export publishes quill's and cib's whole closure. **BUILD-2** is still the owner's decision | part 18, section 7.1 |
| Is the test framework's supply-chain posture sound? | **Yes, and it should stay as it is.** `ut` is MIT, **419 lines** in one header, two contributors, and pinned by an **immutable released tag** - the overlay's `REF dc65567b...` is upstream's `v1.2.1` tag exactly - with a SHA512 on the download and an installed tree that is **byte-identical** to upstream at that SHA (`ut.hpp` sha256 `a13d2278...`). Two things to know: there is **no `ut` port in the vcpkg registry** (at the baseline or on `master`), so the baseline gives it no protection and a bump is a manual act on the portfile; and the bus factor is one (106 of 123 commits). The portfile's `HEAD_REF main` is the loose end - bump only to a **tag**, and change the `REF` and the `SHA512` **together** | part 18, section 7.3 |
| Is quill still the right backend? | **Yes - keep it.** quill 13.1.0 (released 2026-10-17) is the latest release and the registry's version at both the pinned baseline and `master`; it is MIT and actively maintained. The project uses **eight symbols** of it for four things - a lock-free queue, a backend thread, a pattern formatter and a console sink. Two of quill's unused pieces are the ones that matter: **`quill::Codec<Arg>` is an open specialisation point** with a documented contract (`quill/core/Codec.h:164-165`, `:150-161`), which is exactly the extension point **QUIL-1** needs, and `quill::NullSink` exists - the shape item 4's benchmark wants for isolating the producer. The cost is structural: quill bundles its own fmt (`fmtquill`), so two copies of fmt coexist (VCPKG-1). Note that `TransitEvent` is **not** an extension point - its payload is `std::variant<std::monostate, std::atomic<bool>*, double>` (`quill/backend/TransitEvent.h:333`) | part 18, section 7.4 |
| Is `import std;` still behind an experimental CMake gate? | **No - as of CMake 4.5.0 (released 2026-11-12) it is a supported feature.** The `CMAKE_EXPERIMENTAL_CXX_IMPORT_STD` UUID gate is gone from `Help/dev/experimental.rst` and from the cxxmodules manual; the section is marked `.. versionadded:: 4.5`; and the release notes say *"``import std`` is now available for all C++ 20 and later code with `CXX_SCAN_FOR_MODULES` enabled"*. The switch is the `CXX_SCAN_FOR_MODULES` target property, already on for this project. CMake 4.5.0's toolchain matrix also adds **"GCC 16 and newer on MacOS"** - this project's configuration, which 4.4.5 did not list. **The project is on 4.4.5**, so it has to move before it can use it. `MOD-11` is **not** retired: CMake's matrix is not a measurement of this project's configuration | part 18, section 8.4 |
| Does the installed libstdc++ have a `constexpr` `std::format`? | **No** - libstdc++ 16 has `__cpp_lib_constexpr_exceptions 202502L` but **no** `__glibcxx_constexpr_format`, **no** `__cpp_lib_constexpr_format`, and `_GLIBCXX_CONSTEXPR_FORMAT` does not exist in its `<format>` at all. libc++ 21 and libc++ `main` have no `__cpp_lib_constexpr_format` either. **But GCC 17's libstdc++ does**: `__cpp_lib_constexpr_format 202511L` and a `constexpr` `std::format` family (`include/bits/version.def`, `include/bits/version.h`, `include/std/format:67-71`). GCC 17 is **not released** - the horizon is 2027. When it lands, the fmt-over-`std::format` argument weakens from *"neither library"* to *"libc++"*, and the hand-rolled formatter still cannot be retired until libc++ catches up | part 18, section 8.5 |
| Are the five overlay ports still pinned to their upstreams' latest commits? | **Yes - all five are at their upstream's `HEAD` today** (checked 2026-11-12). So the root README's claim is true; the defect is that **nothing detects it**. The four Intel ports are pinned to **`main` branch tips** (their repos publish no tags for these headers), while `ut` is pinned to the immutable **`v1.2.1` tag** - the right shape, and the model the other four should follow | part 18, section 8.1 |

## 13. The items that are answered or contingent

These are the items that **carry an ID** and are no longer open. Section 12 holds the answers to
questions that never had an ID; this section holds the ones that did, so that a reference to
`VCPKG-1` resolves to something. `scripts/audit_index.py` parses this table, and
`scripts/verify_audit.py` fails if an ID appears both here and in an open section.

| # | Question | State | Answer | Evidence |
|---|---|---|---|---|
| VCPKG-1 | Does the upstream vcpkg `quill` port have an opt-in feature for an external fmt? | answered | **No.** At the pinned baseline the upstream `quill` port has **no `features` key at all** and depends only on `vcpkg-cmake` and `vcpkg-cmake-config`; its portfile passes no fmt option. quill 13.1.0's own CMakeLists has no fmt switch either - none of its 26 `option()` calls mentions fmt - and it installs `include/quill/bundled/fmt/*` unconditionally, exposing it as the `fmtquill` interface target. So **the two copies of fmt are structural** | part 18, section 2 |
| VCPKG-2 | Do the five overlay ports shadow builtin vcpkg ports at the pinned baseline? | answered | **No.** The baseline's tree was enumerated in full (17,869 paths, not truncated): none of `ut`, `intel-cib`, `intel-cpp-std-extensions`, `intel-baremetal-concurrency` or `intel-baremetal-senders-and-receivers` appears in `ports/` or in `versions/`. So all five **track upstream rather than the pinned baseline** | part 18, section 2 |
| QUIL-8 | Does the module path flush on every message? | answered | **No, and it never did.** `<true>` means *"honour the per-logger immediate-flush threshold"*, and the check returns immediately when the threshold is 0. The threshold **is** 0 - it defaults to 0 and the project never calls `set_immediate_flush()`. Quill's own default is the same value, so the module path already matches quill's macro-free default | part 18, section 4 |
| BUILD-6 | Are the catalog IDs the same under both compilers? | answered | **Yes - and structurally, not by luck.** The ID is a function of the message text, carried in the message's type, which both compilers spell the same way. All nine catalogs on disk are byte-identical. The *release-to-release* instability is a separate defect - **DEF-6** | part 15 |
| FMT-9 | Does the vcpkg `quill` port have an external-fmt feature? | answered | **No** - the same reading as `VCPKG-1`, which was the same question asked from the installed headers and from the upstream port. The two copies of fmt are structural | part 18, section 2 |
| TOOL-16 | What CI image would provide `gcov-16`? | contingent on `BUILD-5` | **Not a measurement.** The project has no `.github/` directory and no git remote, so the coverage gate, the format check and the clang-tidy check have no home until CI exists. `BUILD-5` ("should there be CI?") is an owner decision and is now **answered: no CI yet**; this question is answered by it, not by a run | part 12 |
| FMT-14 | The module path's format-string dialect: document it, validate it, or move it? | answered | **(c) use fmtlib; single formatter for both paths; depends on QUIL-1** | part 21, decisions.md |
| TOOL-13 | `.cmake-format.yaml` or `.cmake-format.json`? | answered | **YAML — add PyYAML via mise; keep .cmake-format.yaml** | part 21, decisions.md |
| TOOL-14 | Is a one-shot `cmake-format -i` sweep acceptable? | answered | **accept the sweep** — 9 of 12 files change; review diff | part 21, decisions.md |
| BUILD-7 | Where does the stable catalog live? | answered | **(a) use CIB's stable ID mechanism** per logging.adoc / binary_stable_ids | part 21, decisions.md |
| BUILD-1 | What warning flags should the project use? | answered | **all at once** — `-Wall -Wextra -Wpedantic -Wconversion -Wshadow` | part 21, decisions.md |
| BUILD-2 | Should cpp-core be consumable outside this repository? | answered | **add install/export now** — FILE_SET CXX_MODULES + install(EXPORT CXX_MODULES_DIRECTORY) | part 21, decisions.md |
| BUILD-3 | What is the public header surface? | answered | **all three PRIVATE** — only `import com.rsm.logging;` is public | part 21, decisions.md |
| BUILD-4 | Is `clang23` kept? | answered | **conditional** — add clang23 preset + triplet when Homebrew libc++ has `<meta>` | part 21, decisions.md |
| BUILD-5 | Should there be CI? | answered | **no CI yet** — local presets (mise run audit:verify/measure/acceptance) | part 21, decisions.md |
| BUILD-8 | Should the build check the catalog's message set against the call sites? | answered | **yes** — small script, part of coverage work | part 21, decisions.md |
| BUILD-9 | Should the build gain a feature-check gate? | answered | **(c) check only where answer gates code path** (HAVE_REFLECTION, module dialect, import std) | part 21, decisions.md |
| QUIL-9 | What should the public `flush()` say? | answered | **document in both** — module header + README (two-line caveat) | part 21, decisions.md |
| ENV-2 | The abandoned `build/coverage-clang/` | answered | **keep + document** — add README explaining it's abandoned and why | part 21, decisions.md |
| ENV-3 | `ZAI_API_KEY` for the `zai-coding-plan` provider | deferred | **not a cpp-core decision** — defer to owner's agent setup | part 21, decisions.md |
