# The C++26 and third-party features audit

**Date:** 2026-11-11
**Status:** research. Nothing in this directory is applied to the build; it is the evidence and the
recommendations for the three questions the owner asked:

1. Which C++26 or third-party-library features replace hand-rolled code?
2. How should clang-format, clang-tidy, cmake-format and a 100% unit-test-coverage gate be set up?
3. Can the macros be reduced or eliminated in favour of C++26 features, static reflection and
   template metaprogramming?

## The parts

| Part | File | Subject |
|---|---|---|
| 1 | this file | the verdict and the keep / replace / defer table |
| 2 | [intel-libraries.md](intel-libraries.md) | what the Intel libraries in the dependency tree actually provide, header by header |
| 3 | [tooling-design.md](tooling-design.md) | clang-tidy, cmake-format/cmake-lint and the coverage gate: a design note |
| 4 | [import-std.md](import-std.md) | `import std;` and the standard-library-free module rule, against the C++26 text |
| 5 | [reflection.md](reflection.md) | C++26 static reflection (P2996) against the C++26 text |
| 6 | [macro-reduction.md](macro-reduction.md) | what each macro does and whether a template can do it |
| 7 | [coverage-gaps.md](coverage-gaps.md) | what the tests do not reach today, branch by branch |
| 8 | [quill-runtime-formatting.md](quill-runtime-formatting.md) | whether quill can format from a runtime format string, the type-erasure boundary, and a live defect |
| 9 | [constexpr-and-fmt.md](constexpr-and-fmt.md) | fmt over `std::format`, and the per-function `constexpr` / `consteval` inventory |
| 10 | [open-items.md](open-items.md) | **every open question, defect and to-do, in one list** |

## The defect this audit found

**`set_level()` does not filter anything on the module path.** A message logged below the
configured level is still emitted.

Read from the installed quill 13.1.0 headers:

- `Logger::set_log_level` stores the threshold in the **logger**'s `_log_level`
  (`quill/core/LoggerBase.h:142-150`);
- the only reader of that threshold is `should_log_statement`
  (`quill/core/LoggerBase.h:178, 188`), and quill's own wrappers call it - the macro wrapper at
  `LogMacros.h:404`, the function wrapper at `LogFunctions.h:75`;
- **cpp-core's `emit()` calls `log_statement_runtime_metadata` directly, with no check**
  (`src/logging/quill_logger.cpp:113`), and so does the cib path
  (`include/cpp-core/logging/cib_quill.hpp:157`);
- the backend filters against each **sink**'s threshold, not the logger's
  (`quill/backend/BackendWorker.h:1500`), and the sink's default is `TraceL3` - everything passes
  (`quill/sinks/Sink.h:279`).

The logger threshold that `set_level()` sets is therefore read by nobody on this path, and the
sink's threshold stays at its default. The fix is three lines in each of the two call sites, and
`quill::detail::log` (`LogFunctions.h:63-83`) is the reference implementation to copy.

The test suite cannot catch this: it sets the level and reads it back, but never asserts that a
message *below* the threshold is suppressed. That assertion belongs in the coverage work.

**This is a bug, not a trade-off, and it should be fixed whatever else happens.**


## The verdict in one paragraph

The project's own code is in good shape: it defines **no macros of its own**, and the one place a
macro would have been needed - the source location of a log call - was already solved without one
(the defaulted `__builtin_FILE` / `__builtin_LINE` / `__builtin_FUNCTION` parameters of
`format_string` and `log_raw`, a default argument being evaluated at the call site). The
hand-rolled code is concentrated in one file, `modules/logging/format.hpp` (607 lines), and it
exists for **one** reason: the module's interface must not name standard-library types, because a
standard header in the module's global module fragment collides with the importing translation
unit's own standard headers. **That single constraint is what the whole audit turns on**, and it is
now known to be removable on clang-p2996 and not on GCC 16 (see part 4). The honest summary is
therefore:

- **The formatter cannot be replaced by `std::format` yet** - but **not** for the reason the first
  draft of this audit gave. C++26 *does* make `std::format` constexpr: **P3391R2** ("constexpr
  `std::format`") was adopted at the November 2025 Kona meeting, the C++26 draft declares `format`,
  `format_to`, `vformat_to` and `format_to_n` `constexpr`, and the feature-test macro is
  `__cpp_lib_constexpr_format 202511L`. **Neither standard library on this machine implements it** -
  libstdc++ 16 defines no such macro and declares `std::format` without `constexpr`, and libc++ 21
  does the same (llvm#171292 is still open). The underlying reason is that `std::string` is not
  constexpr in either library yet either. So the conclusion stands and the reason changes: **wait
  for the libraries, not for the standard.**
- **The formatter can be replaced at runtime** - by **fmt**, not by `std::format` - with
  `fmt::format_string<Args...>` keeping the compile-time check, *if* the module is allowed to reach
  the library. But fmt cannot enter the module interface either (part 9), so this is a decision
  about the *rest* of the project, not about the module.
- **The project's formatting library is fmt, and `std::format` stays out of the project entirely.**
  The owner's premise is correct and stronger than expected: fmt's compile-time API
  (`FMT_COMPILE`, the `"..."_cf` literal, `FMT_STATIC_FORMAT`) is `constexpr` **including floating
  point**, and `FMT_STATIC_FORMAT` returns a `char[N]`-backed `static_format_result` - so it needs
  **no** constexpr `std::string`, which neither standard library has. C++26's `std::format` excludes
  floats from constant evaluation. fmt cannot enter the module interface (a textual `#include` in a
  module unit yields global-module declarations), so the module keeps its own formatter - but that
  formatter can and should be **`constexpr` throughout**. Part 9.
- **Every function in the module's own formatter can be `constexpr`** - all fifteen of them, and the
  two `consteval` ones stay `consteval`. That turns the formatting rules into `static_assert`s the
  compiler checks on both compilers, with no test binary and no coverage instrumentation - which is
  exactly what the 100% coverage target wants, because it verifies the code the coverage report
  cannot see. Part 9.
- **Static reflection cannot replace anything today**: every `std::meta` range-returning
  metafunction allocates, and neither compiler implements constexpr allocation (P2680 / P1974), so
  a reflection range cannot be walked in a constant expression.
- **The Intel `CIB_*` macros should stay.** The mechanism underneath them is already macro-free -
  `logging::log<Env>` is a function template and `stdx::ct_format<Fmt>` is a variable template -
  and each macro has a macro-free equivalent, but every one of them costs verbosity at the call
  site and buys nothing the project does not already have. The project uses **four** macro
  invocations, all in `src/app.cpp`.
- **The Intel `stdx` constexpr facilities cannot replace the module's hand-rolled compile-time
  scanner**, because they pull in the standard library: `stdx/ct_string.hpp:8-14` includes
  `<array> <concepts> <cstddef> <iterator> <string_view> <type_traits> <utility>`, and
  `stdx/ct_format.hpp` adds `<algorithm>`, fmt and Boost.MP11. The module interface may not have
  any of them.
- **Quill can format from a runtime format string** - `log_statement_runtime_metadata` takes a
  plain `char const*` (`quill/Logger.h:426-431`) - and quill has **no compile-time format-string
  check to lose** (it never uses fmt's compile-time checker), so cpp-core's own `consteval` check
  is strictly stronger and survives either way. The type-erasure boundary is already half built in
  `format.hpp:537-540`; the missing piece is a custom `quill::Codec` that pushes *N* arguments
  from one pack element, which the sources say works and which is the one thing that needs a
  compile to confirm. Part 8.

## The table

| # | Hand-rolled thing | Where | Replace with | Verdict | Why |
|---|---|---|---|---|---|
| 1 | `is_same`, `remove_cvref_t`, `remove_extent_t`, `is_array`, `is_integral`, `is_floating_point`, `is_signed_v`, `type_identity_t` | `format.hpp:20-107` | `std::remove_cvref_t`, `std::remove_extent_t`, `std::is_array_v`, `std::is_integral_v`, `std::is_floating_point_v`, `std::is_signed_v`, `std::type_identity_t` | **keep the hand-rolled ones unless the module may use the standard library** | they are plain language rules, not reflection's job; the only blocker is the standard-library-free rule, not reflection |
| 2 | `convertible_to` concept | `format.hpp:110-113` | `std::convertible_to` | same as #1 | same |
| 3 | `forward` | `format.hpp:129-136` | `std::forward` | same as #1 | same |
| 4 | `message_buffer` (2048-byte stack buffer) | `format.hpp:158-210` | `std::inplace_vector<char, 2048>` | **defer** | `std::inplace_vector` is C++26 but exists in **libstdc++ only**; libc++ 21 has no `<inplace_vector>`. Two compilers must keep working |
| 5 | `scan_format` + `format_matches` (the consteval format-string scanner) | `format.hpp:217-298` | `stdx::ct_format` / `stdx::ct_string` (Intel), or `std::format_string<Args...>` | **keep the hand-rolled scanner** | Intel's `stdx` is ruled out: `stdx/ct_string.hpp:8-14` includes seven standard headers and `stdx/ct_format.hpp` adds `<algorithm>`, fmt and Boost.MP11 - none of which may enter the module interface (part 6). `std::format_string<Args...>` would work, but only if the module may reach the standard library, and it is not `constexpr`-usable at runtime yet in either implementation (see the `std::format` row below) |
| 6 | `format_integer` | `format.hpp:333-426` | `std::to_chars` | **replace if the module may use the standard library** | the hand-rolled version is 94 lines of base/sign/prefix/zero-padding logic |
| 7 | `format_value` (the per-type dispatch) | `format.hpp:428-468` | `std::formatter<T>` / `fmt::formatter<T>` | **replace if the module may use the standard library** | the hand-rolled version is a closed set of `if constexpr` branches; the standard has an extensible `formatter` specialisation point |
| 8 | `parse_spec` (the runtime format-spec parser) | `format.hpp:481-519` | `std::format_to` / `fmt::format_to` | **replace if the module may use the standard library** | 39 lines re-implementing `[[fill]align][sign][#][0][width][.prec][type]` |
| 9 | `format_message` (the field loop) | `format.hpp:536-605` | `std::format_to` / `fmt::format_to` | **replace if the module may use the standard library** | this is the engine the whole file exists for |
| 10 | `format_double` (`snprintf` with `%g`) | `quill_logger.cpp:118-164` | `fmt::format_to_n` | **replace - and fix a divergence** | this translation unit already uses the standard library, so fmt is available here. The hand-rolled version treats `'f'` and the default type alike, so an explicit `{:f}` gives `3.5` where fmt (like `std::format`) gives `3.500000` |
| 11 | `to_quill_level` / `from_quill_level` | `quill_logger.cpp:37-79` and `cib_quill.hpp:63-88` | a single shared mapping | **shrink** | the two mappings are written twice, in two files, in two different type systems (an `int` and cib's `::logging::level`). They cannot be merged as they stand |
| 12 | `decay_enum_value` | `cib_quill.hpp:53-61` | `std::to_underlying` (C++23) | **replace** | `std::to_underlying` is in libstdc++ and libc++ alike; this header is not standard-library-free |
| 13 | the cib tag string built with `std::string` concatenation | `cib_quill.hpp:143-149` | `fmt::format` | **replace** | this header is not standard-library-free, and it is a plain format call. fmt is currently only a **transitive** dependency here - quill 13.1.0 *bundles* its own copy under `quill/bundled/fmt` in the namespace `fmtquill`, and the standalone fmt 12.2.1 in the include tree comes in through `intel-cpp-std-extensions`. Using it directly means declaring `"fmt"` in `vcpkg.json` first - which is step 2 of the plan |
| 14 | `stdx::ct_conversions::type_as_string` / `enum_as_string` | used by nothing today | static reflection, or `stdx::ct_conversions` | **keep `stdx`** | Intel's version is `constexpr` and already a dependency; reflection cannot do it yet (no constexpr allocation) |
| 15 | the `CIB_LOG_MODULE` / `CIB_INFO` / `CIB_WARN` / `CIB_ERROR` macros | `src/app.cpp:21-30` | - | **keep** | part 6: the mechanism underneath is already macro-free (`logging::log<Env>` is a function template, `stdx::ct_format<Fmt>` is a variable template) and every macro has a macro-free equivalent, but each one costs verbosity at the call site and buys nothing. The project uses four macro invocations, all in one file |
| 16 | the `__builtin_FILE` / `__builtin_LINE` / `__builtin_FUNCTION` default arguments | `logging.cppm:68-70`, `:104-105` | `std::source_location::current()` | **keep in the module; use it in the cib path** | `std::source_location::current()` as a default argument is the same idiom, canonicalised. The module may not name `<source_location>`, but the **cib path may** - it already includes `<string>`, `<string_view>` and `<type_traits>`. Part 6, option (e) |
| 17 | the source-location capture itself | `logging.cppm` | - | **already macro-free** | a default argument is evaluated at the call site; this is the standard trick and needs no macro |
| 18 | the whole standard-library-free module rule | `logging.cppm:9-19` | `import std;` | **the one real decision** | part 4: works on clang-p2996 with an empty global module fragment; on GCC 16 every importing translation unit would have to stop including standard headers. Note that the standard *permits* the mixing ([std.modules]/4-5 makes it an implementation obligation), so the GCC failures are deficiencies, not ill-formed programs |
| 19 | the `format_string` class's compile-time check | `logging.cppm:64-84` | `std::format_string<Args...>` | **replace if #18 is adopted** | `std::format_string` is constexpr-constructible, so the compile-time check survives even though `std::format` itself is not `constexpr` **in either implementation on this machine** |
| 20 | `std::meta::nonstatic_data_members_of` | `src/reflection_demo.cpp:23-24` | - | **keep** | it is already the C++26 facility, used for what it is for |

### The formatting library: fmt, and where it can and cannot go

**`std::format` is not used anywhere in this project.** fmt is used everywhere the standard library
is allowed, and the module's own formatter is made `constexpr` instead. Part 9 has the evidence;
the short version:

| | `std::format` (C++26) | fmt 12.2.1 |
|---|---|---|
| constexpr formatting | yes in the standard (P3391R2), **not implemented** in libstdc++ 16 or libc++ 21 | yes, via `fmt/compile.h` |
| **floats at compile time** | **no** - only the integral `std::to_chars` overloads are `constexpr` | **yes** |
| needs a constexpr `std::string` | yes | **no** - `FMT_STATIC_FORMAT` returns a `char[N]`-backed result |
| can it enter the module interface? | no | **no** - a textual `#include` in a module unit yields global-module declarations |

**fmt cannot be `#include`d inside `modules/logging/`** - not even in the purview - on either
compiler. It would need `import std;` (clang-p2996 only) or a fmt module (there is none). So the
module keeps its hand-rolled formatter, and the payoff of fmt is:

1. **outside the module**, fmt replaces `snprintf` in `format_double` (which fixes the `{:f}`
   divergence) and builds the cib tag string;
2. **inside the module**, the hand-rolled formatter becomes fully `constexpr`, which is a
   compile-time guarantee the standard library cannot currently give at all.

**Two copies of fmt coexist.** quill 13.1.0 bundles fmt **12.2.0** in the namespace `fmtquill`
and has no `QUILL_USE_EXTERNAL_FMT` option; the standalone fmt **12.2.1** is in the namespace
`fmt`. The project rule is that **custom formatters are written for `fmt` only** - the cib path
formats primitives and decays its one project type to its underlying integer
(`decay_enum_value`, `cib_quill.hpp:55-61`), so it does not need them.

## What the standard library gives today, on both compilers

Verified on both toolchains (GCC 16.2.0 / libstdc++ and clang-p2996 21.0.0git / libc++):

| Facility | Usable in shared code? | Note |
|---|---|---|
| `std::source_location` | yes | the canonical call-site capture |
| `std::format`, `std::vformat`, `std::print`, `std::println` | yes | usable at runtime; **not** `constexpr` in either implementation on this machine. C++26 *does* make them `constexpr` (**P3391R2**, `__cpp_lib_constexpr_format 202511L`), but libstdc++ 16 and libc++ 21 have not implemented it - and neither has constexpr `std::string`. **Not used by this project**: fmt is the project's formatter (part 9) |
| `fmt::format`, `fmt::compile`, `fmt::format_to_n` | yes - outside the module | fmt 12.2.1; **not** usable inside the module interface. `FMT_STATIC_FORMAT` is `constexpr` and needs no constexpr `std::string` |
| `std::expected`, `std::optional`, `std::ranges` | yes | `constexpr` |
| `std::to_underlying`, `std::byteswap` | yes | `constexpr` |
| `constexpr std::string_view` | yes | `constexpr` |
| `constexpr` virtual functions (P2361) | yes | |
| `static operator()` (P1169, C++23) | yes | |
| `std::inplace_vector`, `std::function_ref`, `std::generator`, `std::move_only_function` | **GCC only** | libc++ 21 has none of them |
| `std::text_encoding`, `std::simd`, `std::stacktrace` | **no** | absent or gated off in libc++; `simd` is x86-only here, `stacktrace` is off on macOS |
| `std::meta` ranges walked at compile time | **no** | no constexpr allocation (P2680 / P1974) |
| `constexpr std::string` / `constexpr std::vector` | **no** | P2278 is not implemented |
| Intel `stdx` (`ct_format`, `ct_string`) inside the module interface | **no** | `stdx/ct_string.hpp:8-14` includes seven standard headers; `stdx/ct_format.hpp` adds `<algorithm>`, fmt and Boost.MP11 |

## The tooling, in one table

| Tool | Verdict | The one thing that decides it |
|---|---|---|
| clang-format | **done** - `61ba2da` | the configuration was glaze's and had never been run; it is now derived from the code and the tree is conformed |
| clang-tidy | **check the non-module translation units only** | clang-tidy cannot consume a module interface unit: the co_compile invocations are unconsumable (llvm#62258), and the module's binary is locked to the clang that built it (llvm#63939) |
| cmake-format | **run it, but the diff is large** | it would rewrite 9 of the 12 CMake files; the same "accept the reformat" decision as clang-format applies |
| cmake-lint | **run it** | 19 line-length findings, 9 naming findings, one false positive (`RANGE <stop>`) and one missing `COMMENT` |
| coverage | **GCC 16 + `gcov-16` + a stdlib-only Python gate** | clang's raw profile is v10 and `llvm-profdata` 23.1.5 wants v11; `gcovr` is broken on this machine; `lcov` is absent |

## The honest 100% coverage

"100%" has to mean something precise, or it is a slogan. The design note (part 3) defines it as:
**every instrumented line of the project's own code - module interface, library, application -
executed at least once by the test suite**, with a small, reviewed exclusion list for code that is
compile-time only. It is *not* branch coverage, not the dependencies, not the test code itself.

The baseline today is not 100%. The tests exercise `info`, `warning`, `error`, `log_raw`, the
level get/set, `setup` and `flush`. They do **not** exercise `trace`, `debug` or `critical`, the
level filtering, almost any format specification, the 2048-byte buffer truncation, the
`self_formatting` path, the cib/catalog path, or the internals of `quill_logger.cpp`. The gate is
therefore a to-do list as much as a tool: extend the tests until the measured uncovered list is
empty.

## The open questions

**They are all in one place now: [open-items.md](open-items.md)** - part 10. It has every open
question, every known defect and every to-do, grouped and numbered (`DEF-`, `FMT-`, `QUIL-`,
`TOOL-`, `MOD-`, `REFL-`, `MAC-`, `COV-`, `ENV-`), each with what settles it.

In summary, and all of it needs a compile, a run, or an owner decision:

| Area | Items | The load-bearing one |
|---|---|---|
| **The defects** | 3 | `DEF-1`: `set_level()` filters nothing on the module path - a bug, three lines at each of two call sites |
| **fmt and `constexpr`** | 12 | `FMT-4` / `FMT-5`: can `format.hpp` be made `constexpr` wholesale, and does the `static_assert` pattern work? The compiler is the test |
| **quill's runtime formatting** | 8 | `QUIL-1`: can a `quill::Codec` push three arguments from one pack element? It decides whether the 607-line formatter can shrink |
| **The tooling** | 16 | `TOOL-6`: does GCC 16 emit arcs for uninstantiated templates and `consteval` bodies? It decides whether the coverage numbers can be trusted at all |
| **`import std;`** | 9 | `MOD-6`: is the GCC 16 failure an artefact of CMake not building header units, or a merge deficiency? |
| **Static reflection** | 4 | `REFL-1`: do the two compilers' `members_of` forms compile the same source? |
| **The macros** | 3 | `MAC-1`: does `std::source_location::current()` in a default argument return the *caller's* location through the `logging::log<Env>` template? It may be why the CIB macro cannot be dropped |
| **Coverage to-dos** | 10 | the uncovered set, branch by branch - and the `constexpr` change removes half of it from the runtime problem |
| **The environment** | 3 | `ENV-1`: the two copies of fmt, and the rule that custom formatters are written for `fmt` only |

Two more that were answered in the first draft and are recorded in part 10, section 10: GCC throws
`std::meta::exception` ("reflection with has_identifier false") for `std::meta::identifier_of` on a
plain type reflection, and `std::source_location::current()` returns an empty `function_name()` in a
`constexpr` context.

The first thing to run when the build lane reopens is in [PARKED.md](../../PARKED.md).

## The corrections this audit made to itself

Two claims in the first draft of this audit were wrong, and both are load-bearing. They are
recorded here because a document that hides its own corrections is not much use to a reviewer.

**1. "`std::format` is not `constexpr` in C++26 (P2210R2)" - wrong on both counts.** P2210R2 is
"Superior String Splitting", an unrelated paper. The real paper is **P3391R2**, "constexpr
`std::format`", which was **adopted into C++26** at the November 2025 Kona meeting. The C++26
draft's synopsis declares `format`, `format_to`, `vformat_to` and `format_to_n` `constexpr`, and
the feature-test macro is `__cpp_lib_constexpr_format 202511L` (the draft also defines
`__cpp_lib_constexpr_string 202511L`).

The *conclusion* survives, but the *reason* changes: **neither standard library on this machine
implements P3391R2.** libstdc++ 16 defines no `__cpp_lib_constexpr_format` and declares
`std::format` without `constexpr`; libc++ 21 defines no such macro either (`__cpp_lib_format` is
still `202110L`) and llvm#171292 is still open. The underlying reason is that `std::string` is not
constexpr in either library yet either.

**2. "A module's global module fragment is copied into every translation unit that imports it."**
This is the wording in `modules/logging/logging.cppm:9-19` and in this audit's first draft. It
describes the *observed failure mode* accurately, but it is **not what the standard says**. The
draft says the global module fragment "can be used to provide declarations that are attached to
the global module and usable within the module unit" ([module.global.frag]/1), and it makes the
mixing of `#include` and `import` an implementation obligation: "Conforming implementations ensure
that mixing #include and import does not result in conflicting attachments" ([std.modules]/4) and
"A declaration in the standard library denotes the same entity regardless of whether it was made
reachable through including a header, importing a header unit, or importing a C++ library module"
([std.modules]/5).

So the GCC 16 failures are **implementation deficiencies, not ill-formed programs**, and the
repository's comment overstates the standard's rule. The design conclusion is unchanged - and
arguably stronger, because a deficiency is something a project has to work around until it is
fixed upstream, whereas a rule violation would be the project's own fault.

**3. The Intel `stdx` constexpr formatting is the most promising replacement for the module's
hand-rolled scanner.** It is not: `stdx/ct_string.hpp:8-14` includes seven standard headers and
`stdx/ct_format.hpp` adds `<algorithm>`, fmt and Boost.MP11, so `stdx` cannot enter the module
interface at all. See part 6.

## The method

Every claim in this directory is one of:

- **[doc]** - read from a documentation page, a release note or the C++26 working draft, with a URL;
- **[source]** - read from an installed header or a tool's own source, with file:line;
- **[measured]** - observed on this machine by running a tool against the repository (a formatter, a
  linter, a coverage tool - never a build of the project itself);
- **[inferred]** - reasoning from the above, always flagged as such.

Anything that could only be settled by compiling the project is in the open questions above
instead of being asserted.
