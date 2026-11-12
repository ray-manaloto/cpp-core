# The open items and known issues

**Date:** 2026-11-11
**Status:** the single list of everything the audit could not settle, plus every defect and to-do it
found. Each item says what settles it and where it came from.

**Everything in this list needs a compile, a run, or an owner decision.** The build lane is parked,
so none of it has been applied. The items are ordered by the plan they belong to, and the plan
itself is in [README.md](README.md) and [PARKED.md](../../PARKED.md).

Two kinds of item are mixed here on purpose:

- **issues** - something is wrong today and should be fixed (section 1);
- **open questions** - something is not known yet and needs a measurement (sections 2 to 8).

## 1. The issues - known defects, to fix

### DEF-1 - `set_level()` filters nothing on the module path

**A message logged below the configured level is still emitted.** This is a bug, not a trade-off.

The chain, read from the installed quill 13.1.0 headers:

| Step | Where | What |
|---|---|---|
| `set_level()` writes | `quill/core/LoggerBase.h:142-150` | the threshold into the **logger**'s `_log_level` |
| the only reader | `quill/core/LoggerBase.h:178, 188` | `should_log_statement` |
| quill's own wrappers call it | `LogMacros.h:404`, `LogFunctions.h:75` | so quill's own paths filter correctly |
| **cpp-core's `emit()` does not** | `src/logging/quill_logger.cpp:113` | calls `log_statement_runtime_metadata` directly |
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
| FMT-9 | Does the vcpkg `quill` port have an external-fmt feature? The installed headers say no; the upstream port might. If it does, the two-copies problem disappears | reading the vcpkg port |
| FMT-10 | Does `std::source_location::current()` in a default argument on `quill_config::logger::log` return the **caller's** location, given that the call goes through the `logging::log<Env>` template? It may be the reason the CIB macro cannot be dropped | a compile - **also MAC-1** |
| FMT-11 | Does the catalog tooling's `nm` scan still find the same undefined `catalog<>` / `module<>` symbols if the cib tag string is built with `fmt::format`? The tags are runtime data, not types, so it should not matter | a run - **also MAC-2** |
| FMT-12 | Does `fmt::runtime` exist in fmt 12.2.1's public API under that name, and is it the right way to format a runtime-built specification in `format_double`? | reading the header, plus a compile |

## 3. quill's runtime formatting (QUIL)

From [quill-runtime-formatting.md](quill-runtime-formatting.md).

| # | Question | Settled by |
|---|---|---|
| QUIL-1 | Does a `Codec` that pushes three arguments from one pack element satisfy a `"{} {} {}"` statement? **This is the load-bearing unknown for the whole formatter rewrite** | one scratch translation unit |
| QUIL-2 | Which types can be pushed into `DynamicFormatArgStore` without a formatter - `bool`, `char`, the signed and unsigned 8/16/32/64-bit integers, `float`, `double`, `long double`, `void const *`, `string_view`? And does a scoped `enum` push as its underlying integer, or does it need a formatter? (The cib path already has `decay_enum_value` at `cib_quill.hpp:55-61` for this reason) | a compile |
| QUIL-3 | Exactly which default-specification outputs change between the module's `snprintf("%g")` and fmt's shortest round-trip? | a run - **overlaps FMT-6** |
| QUIL-4 | Does fmt render the whole specification cross-product identically to the module's `parse_spec` - in particular `#` with `b`/`x`/`o`, `0` padding combined with a sign, `^` centring, and precision on a string (fmt truncates; the module clamps in `copy_text`, `format.hpp:304-316`)? | a compile and a differential test |
| QUIL-5 | Can the module's `format_string` hold a compile-time-rewritten template - a struct with a `char[N]` member and no standard-library types - so that the pre-formatted fields become `{}` and the pass-through fields keep their specification? This is what the `self_formatting` path needs | a compile |
| QUIL-6 | Will the compiler accept a `char const[N]` with no terminator at the `consteval format_string` boundary (`logging.cppm:67`)? If it will, option (b) introduces an out-of-bounds read in quill's `safe_strnlen` that is impossible today, and the consteval check would have to require `text[N-1] == '\0'` | a compile |
| QUIL-7 | Does a message over 2047 bytes behave acceptably on the default `UnboundedBlocking` queue, and would a bounded queue throw `QuillError` (`Logger.h:871-882`) where the message is silently truncated today? | a run |
| QUIL-8 | `emit()` hard-codes `<true>` for the immediate-flush template parameter (`quill_logger.cpp:117`). Should the module path flush on every message, or match quill's macro-free default? That is a throughput decision | a measurement, not a guess |

## 4. The tooling (TOOL)

From [tooling-design.md](tooling-design.md) sections 3.6 and 5. Q1-Q7 in section 3.6 are the
coverage run; the rest are clang-tidy, cmake-format and the CI.

| # | Question | Settled by |
|---|---|---|
| TOOL-1 | Does the proposed `.clang-tidy` pass `clang-tidy --verify-config` on Homebrew 23.1.5, and does `clang-tidy -p <build> --config-file=.clang-tidy src/app.cpp` exit non-zero on any enabled-check warning with `WarningsAsErrors` enabled? Does it parse the p2996 `compile_commands.json` without the `-freflection` `RemovedArgs` hack, and with it? | a run |
| TOOL-2 | Can clang-tidy parse `modules/logging/logging.cppm` at all, standalone with `-x c++-module`? If yes, is the diagnostic output usable (do the enabled checks skip module declarations via `SkipDeclsInModules`, PR #145630 - and is that in 23.1.5)? The default stays "do not check the `.cppm`" until it is measured | a run |
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
| TOOL-13 | `.cmake-format.yaml` versus `.cmake-format.json`: if the YAML route is kept, the pipx install must gain pyyaml (`mise use pipx:cmakelang[yaml]` or a project `.mise.toml`). **Owner decision**: who pins it, or do we commit JSON? The YAML config crashes on this machine without PyYAML | an owner decision |
| TOOL-14 | Is a one-shot `cmake-format -i` sweep acceptable? 9 of the 12 CMake files change. Do we keep hand-wrapping via `.cmake-format.yaml` and `always_wrap` (never collapse `add_custom_target`), or accept cmake-format's canonical layout? Measure the post-conformance diff in review | an owner decision |
| TOOL-15 | Does `.clang-format` and `.cmake-format.yaml` agree on anything besides `line_width = 100`? (`tab_size`, `line_ending`, markup-off / reflow-off.) Cosmetic, but worth editing together | a run |
| TOOL-16 | Does CI (a GitHub Actions runner) provide `gcov-16` at a known path, or via `ubuntu-latest`'s GCC? If not, the gate must either install GCC 16 in CI or stay a local/preset gate for now | a run |

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
| COV-1 | `trace`, `debug` and `critical` - none of the three is called by any test | `logging.cppm:86-151` |
| COV-2 | The level-filtering branches, and the assertion that a message below the threshold is suppressed - **this is DEF-1's test** | `quill_logger.cpp:105-119` |
| COV-3 | Almost every format specification: alignment and fill, sign, `#`, zero padding, precision, `x`/`X`/`o`/`b`, uppercase digits, `^` centring | `format.hpp` |
| COV-4 | The 2,048-byte buffer truncation | `format.hpp:158-210` |
| COV-5 | The `self_formatting` path - no `self_formatting` type exists in the codebase today | `format.hpp:424-468` |
| COV-6 | The `is_array` and `string_like` branches | `format.hpp:20-107` |
| COV-7 | The cib/catalog path - `demo::run()` in `src/app.cpp` is never called by any test; the catalog IDs are produced but never executed | `src/app.cpp`, `cib_quill.hpp` |
| COV-8 | The internals of `quill_logger.cpp`: logger-creation races, the `current_level` getter's edge cases | `quill_logger.cpp` |
| COV-9 | `src/reflection_demo.cpp` is compiled, but its runtime line only runs if reflection works at runtime (it does) - and nothing calls it in the tests | `src/reflection_demo.cpp` |
| COV-10 | `log_raw`'s length path is only partially exercised | `logging.cppm:104-107` |

**The `constexpr` change removes half of this from the runtime-coverage problem.** With
`format.hpp` `constexpr`, every formatting rule becomes a `static_assert` that the compiler checks,
on **both** compilers, with no test binary and no coverage instrumentation. That is a stronger
guarantee than a runtime test, and it is exactly what a 100% coverage target wants: the
compile-time-only code the coverage report cannot see gets verified instead.

## 9. The environment (ENV)

| # | Item | Settled by |
|---|---|---|
| ENV-1 | The two copies of fmt: the standalone `fmt` 12.2.1 (namespace `fmt`) and quill's bundled `fmtquill` 12.2.0. **The project rule is that custom formatters are written for `fmt` only**; the cib path formats primitives and decays its one project type to its underlying integer | a decision now, revisited at FMT-9 |
| ENV-2 | `build/coverage-clang/` - an abandoned experiment. The raw-profile version mismatch (clang v10 against `llvm-profdata` 23.1.5's v11) makes it unusable; it can be deleted | an owner decision |
| ENV-3 | `ZAI_API_KEY` for the `zai-coding-plan` provider: the two saved `Z.AI` accounts in `opencode auth list` belong to the `zai` integration, not to `zai-coding-plan`, so they do not satisfy it. Either `opencode service set env ZAI_API_KEY <key>` (stops and restarts the background service) or `opencode auth login zai-coding-plan` (a saved account, no restart). The local `opencode.json` registers only `glm-4.7` for that provider; `glm-5.3` and `glm-5.3-flash` are in the catalog and would have to be added | an owner decision |

## 10. What is *not* an open question

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
