# Parked

The owner paused every implementation lane except the plugin and MCP setup. **cpp-core has an
exception: research continues** - reading, web and doc research, notes and write-ups. There is to
be no compiler work: no builds, no compiler or toolchain installs or configuration, no CMake or
preset build runs, no test or ASan runs. If a research step would need a compile to check
something, it is written down as a question for later instead.

This file records where the cpp-core work stands so it can be picked up without re-deriving
anything.

## The three-part request that is open

1. C++26 / third-party-library features that replace hand-rolled code.
2. clang-format, clang-tidy, cmake-format and 100% unit-test coverage set up.
3. Macros reduced or eliminated in favour of C++26 features, static reflection and templates.

**The research for all three is now done and written down**, including the two follow-up decisions
the owner added: **fmt over `std::format`**, and **everything `constexpr` / `consteval` wherever
possible**. What remains is the implementation, which is parked.

## Done and committed

- Item 1 of the earlier request (ASan leak check on `p2996-asan`): `fd79fc0`, `87d2fcf`.
- Item 2 of the earlier request (macro-free source location in the module): `8800b0a`.
- **clang-format configuration (this step)**: `61ba2da`.
  - `.clang-format` was glaze's config and was never run; the code uses a different style.
  - It is now derived from the code: 2-space indent, attached braces, right-aligned pointers and
    references, 100-column limit, include blocks preserved (they are grouped by hand).
  - The tree is conformed (131 lines changed, mostly pre-existing internal inconsistency).
  - Verified: `clang-format --dry-run --Werror` is clean; `p2996-debug` and `gcc16-debug` build and
    their tests pass.
  - Tools on this machine: `clang-format` / `clang-tidy` 23.1.5 in `/opt/homebrew/opt/llvm/bin`;
    `cmake-format` / `cmake-lint` 0.6.13 (mise `pipx:cmakelang`, not pinned in any config, so the
    shims fail with "No version is set" - it has to be found by path or a project `.mise.toml`
    added and trusted); `gcov-16` in `/opt/homebrew/opt/gcc/bin`; no `lcov`/`genhtml`.
- `.editorconfig` made to agree with the formatter: `2ef42de`.
- The features audit, in sixteen parts: `3d7e865`, `15be31c`, `0e414de`, plus the parts written
  since (reflection, macro reduction, fmt and `constexpr`, the consolidated open-items list).
- The SDLC subagent role definitions: `22b6a65`.

## The research lane - complete

`docs/cxx26-features-audit/`:

| Part | File | Subject |
|---|---|---|
| 1 | [README.md](docs/cxx26-features-audit/README.md) | the verdict and the 20-row keep / replace / defer table |
| 2 | [intel-libraries.md](docs/cxx26-features-audit/intel-libraries.md) | what the Intel libraries in the dependency tree provide, header by header |
| 3 | [tooling-design.md](docs/cxx26-features-audit/tooling-design.md) | clang-tidy, cmake-format/cmake-lint and the coverage gate |
| 4 | [import-std.md](docs/cxx26-features-audit/import-std.md) | `import std;` and the standard-library-free rule, against the C++26 text |
| 5 | [reflection.md](docs/cxx26-features-audit/reflection.md) | C++26 static reflection (P2996) against the C++26 text |
| 6 | [macro-reduction.md](docs/cxx26-features-audit/macro-reduction.md) | what each macro does, and whether a template can do it |
| 7 | [coverage-gaps.md](docs/cxx26-features-audit/coverage-gaps.md) | what the tests do not reach today, branch by branch |
| 8 | [quill-runtime-formatting.md](docs/cxx26-features-audit/quill-runtime-formatting.md) | quill's runtime formatting, the type-erasure boundary, and the defect below |
| 9 | [constexpr-and-fmt.md](docs/cxx26-features-audit/constexpr-and-fmt.md) | fmt over `std::format`, and the `constexpr` inventory |
| 10 | [open-items.md](docs/cxx26-features-audit/open-items.md) | **every open question, defect and to-do, in one list** |
| 11 | [cxx26-library-availability.md](docs/cxx26-features-audit/cxx26-library-availability.md) | the verified C++26 library sweep against both toolchains' headers |
| 12 | [build-and-dependencies.md](docs/cxx26-features-audit/build-and-dependencies.md) | the vcpkg overlays, the triplets and the CMake - the build as a subject |
| 13 | [format-dialect.md](docs/cxx26-features-audit/format-dialect.md) | the module path's format strings against the C++26 grammar and fmt's - and the two paths' disagreement |
| 14 | [remaining-research.md](docs/cxx26-features-audit/remaining-research.md) | the four questions that needed no compile: Intel's `stdx`, the logger's lifetime, `ut`'s module, the upstream watch |
| 15 | [catalog-ids.md](docs/cxx26-features-audit/catalog-ids.md) | are the catalog IDs the same under both compilers? - and why they are not the same between releases |
| 16 | [readme-check.md](docs/cxx26-features-audit/readme-check.md) | the root `README.md`, checked line by line - and the proof that the committed tree is the tree that built |
| 17 | [decisions.md](docs/cxx26-features-audit/decisions.md) | the thirteen decisions the owner has to make, with a recommendation for each |

The upstream sources those parts quote are vendored under
[`docs/cxx26-features-audit/upstream/`](docs/cxx26-features-audit/upstream/README.md), so the review
can be done offline.

### The decisions the owner added, and what they mean

**Use fmt, not `std::format`.** The premise is correct and stronger than expected:

- fmt's compile-time API (`FMT_COMPILE`, the `"..."_cf` literal, `FMT_STATIC_FORMAT`) is
  `constexpr` **including floating point**. C++26's `std::format` excludes floats from constant
  evaluation - only the *integral* overloads of `std::to_chars` are `constexpr` (P2291R3).
- `FMT_STATIC_FORMAT` returns a `fmt::static_format_result<N>`, which holds a `char data[N]`
  (`fmt/compile.h:565-578`). So it needs **no** constexpr `std::string` - which neither standard
  library has.
- `std::format` *is* `constexpr` in C++26 (**P3391R2**, adopted at Kona in November 2025,
  `__cpp_lib_constexpr_format 202511L`), but **neither library here implements it**: libstdc++ 16
  and libc++ 21 both lack the macro, and llvm#171292 is open. Wait for the libraries, not for the
  standard.
- **fmt cannot enter the module interface.** A textual `#include` in a module unit yields
  global-module declarations, which collide with the importing translation unit's own standard
  headers - the same failure the standard library has. `fmt/base.h` includes `<string>`,
  `<string_view>`, `<memory>`, `<iterator>`, `<type_traits>` and more. So the module keeps its own
  formatter, and the fmt switch is about the rest of the project.

**Make everything `constexpr` / `consteval` wherever possible.** The inventory is in part 9. The
short version:

| Where | What | Verdict |
|---|---|---|
| `modules/logging/format.hpp` | all fifteen functions | **all can be `constexpr`**; `scan_format` and `format_matches` stay `consteval` |
| `src/logging/quill_logger.cpp` | `to_quill_level`, `from_quill_level` | **`constexpr`** |
| `src/logging/quill_logger.cpp` | `format_double` | **cannot** be `constexpr` - `std::snprintf` is a library call and `std::to_chars` for floats is not `constexpr` in C++26 |
| `include/cpp-core/logging/cib_quill.hpp` | `decay_enum_value` | **`constexpr`** (the others already are) |
| everything that starts the backend, queues a message or allocates | | **cannot** be `constexpr` - and must not be |

**Why it is worth more than a keyword:** every formatting rule becomes a `static_assert` that the
compiler checks, on **both** compilers, with no test binary and no coverage instrumentation. That
turns "the tests do not reach the formatter" from a coverage problem into a compiler-checked
guarantee - and it is exactly what a 100% coverage target wants.

**Two caveats** (part 9, section 2.3):

1. `format_value`'s floating-point branch calls `format_double`, so a **float argument cannot be
   constant-evaluated**. The function is still legal as `constexpr`.
2. `format_message` takes the addresses of its arguments (`format.hpp:537-540`), so in a constant
   expression the arguments must be `constexpr` objects of **static storage duration**. A temporary
   argument will not constant-evaluate. That constrains the shape of the `static_assert` tests, not
   the design.

### A live defect, found by reading quill's headers

**`set_level()` does not filter anything on the module path.** A message below the configured level
is still emitted. The chain: `Logger::set_log_level` sets the *logger's* threshold
(`quill/core/LoggerBase.h:142-150`); the only reader is `should_log_statement`
(`LoggerBase.h:178, 188`); quill's macro wrapper (`LogMacros.h:404`) and function wrapper
(`LogFunctions.h:75`) call it, but cpp-core's `emit()` (`src/logging/quill_logger.cpp:113`) and the
cib path (`include/cpp-core/logging/cib_quill.hpp:157`) call
`log_statement_runtime_metadata` directly; the backend filters against each *sink's* threshold
(`BackendWorker.h:1500`), whose default is `TraceL3` (`Sink.h:279`).

**This is a bug, not a trade-off.** The fix is three lines in each of the two call sites, copying
`quill::detail::log` (`LogFunctions.h:63-83`). It needs the test "a message below the configured
level is not emitted" - which the suite does not have and which would fail today.

### The findings that decide the rest

1. **`import std;` works on both toolchains** (CMake 4.4.5's experimental gate,
   `CMAKE_EXPERIMENTAL_CXX_IMPORT_STD "f35a9ac6-8463-4d38-8eec-5d6008153e7d"`, `CXX_MODULE_STD ON`,
   Ninja >= 1.11), but it removes the standard-library-free constraint **only on clang-p2996**. On
   GCC 16 every importing translation unit would have to stop including standard headers.
   **The standard permits the mixing** ([std.modules]/4-5 makes it an implementation obligation),
   so the GCC failures are deficiencies, not ill-formed programs - and the repository's own
   comment about the global module fragment overstates the standard's rule.
2. **Static reflection cannot replace anything today**: every `std::meta` range-returning
   metafunction allocates, and neither compiler implements constexpr allocation (P2680 / P1974), so
   a reflection range cannot be walked in a constant expression.
3. **Intel's `stdx` cannot enter the module interface**: `stdx/ct_string.hpp:8-14` includes seven
   standard headers and `stdx/ct_format.hpp` adds `<algorithm>`, fmt and Boost.MP11.
4. **The CIB macros stay.** The mechanism underneath them is already macro-free, and each macro
   has a macro-free equivalent - but every one costs verbosity at the call site. The project uses
   four macro invocations, all in `src/app.cpp`. The one cheap improvement is
   `std::source_location` in the cib path, which is not standard-library-free.
5. **Quill can format from a runtime format string** (`log_statement_runtime_metadata`, `Logger.h:426-431`)
   and has no compile-time format-string check to lose, so cpp-core's own `consteval` check
   survives either way. The type erasure is already half built (`format.hpp:537-540`); the missing
   piece is a custom `quill::Codec` pushing *N* arguments from one pack element - the one thing
   that needs a compile.

## Not started (the next steps, in order)

When the build lane reopens:

1. **Fix the level-filtering defect** and add the test "a message below the configured level is not
   emitted". Three lines in each of the two call sites; the test would fail until it is fixed.
2. **Add `"fmt"` to `vcpkg.json`** as a direct dependency. It is currently transitive only, through
   `intel-cpp-std-extensions`, and quill bundles its own copy under `quill/bundled/fmt` in the
   namespace `fmtquill`. One line - and **free**: fmt 12.2.1 is already installed, so this is a
   manifest change with no download, no version change and no port rebuild (part 12).
3. **Mark the fifteen `format.hpp` functions `constexpr`.** About fifteen keywords, no signature
   change, no behaviour change. The compiler is the test.
4. **Add the `static_assert` formatter tests.** A new file (or a block in the existing test file);
   no test framework and no runtime needed. The arguments must be `constexpr` objects of static
   storage duration.
5. **Replace `std::snprintf` with fmt in `format_double`.** This fixes the `{:f}` divergence:
   `format_double` treats `'f'` and the default type alike and uses `%g`, so `{:f}` gives `3.5`
   where fmt (like `std::format`) gives `3.500000`. The format specification is a runtime `char`
   here, so this uses `fmt::runtime` - it is about correctness, not constexpr-ness.
6. **Use `fmt::format` for the cib tag string** (`cib_quill.hpp:146-148`). Three lines.
7. **Then, and only then, consider the big one:** moving the formatting to the implementation TU
   (part 8). It needs the `quill::Codec` experiment to succeed, and it is the only step that
   changes the module's design. Steps 3-6 make the current design better whether or not it happens.

**After that**, the tooling and coverage work, which is a separate track:

8. **Wire the formatting into CMake** - `cmake/format.cmake` with the `format`, `format-check`,
   `cmake-format` and `cmake-lint` targets, modelled on `cmake/iwyu.cmake` (one target per check,
   opt-in via a cache variable, a preset to turn it on). Needs `.clang-tidy` and
   `.cmake-format.yaml` - **as JSON**, because the pipx cmakelang venv on this machine has no
   PyYAML and the YAML config crashes.
9. **Coverage** - the viable route is GCC 16 `-fprofile-arcs -ftest-coverage` plus `gcov-16`;
   clang's raw profile is v10 and the installed `llvm-profdata` 23.1.5 expects v11, so
   `llvm-cov` cannot be used. A script computes the line coverage and fails the build below the
   threshold. The uncovered list to close is in part 7 and part 10, section 8 - and step 3 and 4
   above remove a good part of it from the runtime problem.
10. **The `import std;` decision** - keep the status quo (option (a)), with the module's interface
    standard-library-free and the standard-library-dependent work behind
    `include/cpp-core/logging/internal.hpp`, which already exists for that purpose. Revisit if
    libstdc++ fixes its mixing deficiency; the design should keep that option cheap.

## The open items, in one place

**[docs/cxx26-features-audit/open-items.md](docs/cxx26-features-audit/open-items.md)** has all of
them: 6 defects, 14 fmt/`constexpr` questions, 8 quill questions, 16 tooling questions, 9
`import std;` questions, 4 reflection questions, 3 macro questions, 10 coverage to-dos, 7 build
questions and 3 environment questions - **80 in all** - each with what
settles it, plus a table of the questions that are **not** open because they have already been
answered. (It was 83 until part 18 answered the two dependency-tree questions and the
immediate-flush question; see below.)

## What parts 11 and 12 changed

**Part 11 - the standard library, verified.** A sweep of the C++26 library facilities against the
two trees the project's own compilers use (libstdc++ 16 at
`/opt/homebrew/Cellar/gcc/16.2.0/include/c++/16`, libc++ 21 in the p2996 toolchain). **22
facilities are declared in both, 9 in libstdc++ only, 0 in libc++ only, 5 in neither** (`std::simd`,
`std::linalg`, constexpr `std::format`, `std::containers`, `std::from_chars` for floating point).
Two corrections to the audit's own table:

- **constexpr `std::string` / `constexpr std::vector`**: the verdict ("no") stands, but the reason
  was imprecise. Both libraries declare the macros - it is the *partial* constexpr (construct a
  string, construct and clear a vector), with no constexpr mutation and no constexpr allocation.
  Neither can build a `std::string` by formatting at compile time, which is what the project wants.
- **`std::from_chars` for floating point is in neither library.** `to_chars` for floats *is* in
  both - libc++ 21 has the overloads (`charconv:39-50`) but never bumped `__cpp_lib_to_chars` off
  the C++17 value, so the macro under-reports it. Neither is `constexpr` (P2291R3 made only the
  integral overloads so).

Two traps are documented because they are easy to fall into again: libc++'s `<version>` opens with
a **synopsis block** that lists unimplemented features as if they existed (its `<inplace_vector>`
entry is commented out at `version:573`), and both libraries define their macros inside
per-standard-version branches, so "the last `#define` in the file" picks the **oldest** branch.

**Part 12 - the build, which the audit never treated as a subject.** Ten findings, of which these
change the plan:

- **`fmt` is already installed** - `intel-cpp-std-extensions` depends on it. Step 2 of the plan
  (adding `"fmt"` to `vcpkg.json`) is a one-line manifest change with **no download and no port
  rebuild**.
- **The two copies of fmt are structural.** The vcpkg `quill` port installs only
  `quill/bundled/fmt/`, so quill's `fmtquill` and the standalone `fmt` coexist whatever the
  project does. The rule stands: custom formatters are written for `fmt` only.
- **There are no compiler warning flags at all** - not `-Wall`, not `-Wextra`. That is a gap next
  to a clang-tidy plan, but adding warnings is a behavioural change, so it is the owner's call
  (`BUILD-1`).
- **There are no install or export rules**, and the "public" header surface is an accident:
  `quill_logger.hpp` is published under `include/` and pulls in `<quill/Logger.h>`, although its
  own comment calls it implementation-private (`BUILD-2`, `BUILD-3`).
- **`clang23` is unreachable** - the toolchain and the configure check accept it, but it has no
  triplet and no preset. Part 3's clang-tidy design needs Homebrew clang 23 to build a BMI with
  (`BUILD-4`).
- **There is no CI and no git remote**, so the coverage, format and tidy gates have nowhere to run
  and `TOOL-16`'s question about a CI image is moot (`BUILD-5`).
- **The catalog IDs may not be stable across compilers** - `gen_str_catalog` derives them from
  `nm`, whose output depends on the compiler's mangling (`BUILD-6`).

## What parts 13 and 14 changed

**Part 13 - the format-string dialect.** The project runs **two** format-string dialects at once,
and they do not agree. The module path uses the module's own scanner; the catalog path uses quill's
bundled fmt, which implements the C++26 format-spec grammar and checks it against the argument's
type. Part 13 compares the three grammars - the standard's, fmt's and the module's - and lists
fifteen differences (D1-D15). Two of them change output today:

- `info("{:>06}", 42)` gives **"000042"** on the module path and **"    42"** on the catalog path
  (the standard says the `0` is ignored when an alignment is given; fmt says so in a comment, and
  the module does not);
- `info("{}", 1234567.0)` gives **"1.23457e+06"** on the module path and **"1234567"** on the
  catalog path - the module's default is `%g`, six significant digits, where the standard's is the
  shortest round-trip. **This is DEF-2 seen from the other side: the default is wrong too, and the
  default is what every unadorned `{}` uses.** (Step 5 of the plan fixes this one in both paths,
  because the module's float formatting already happens in the implementation TU, in
  `format_double`.)

And one of them is not a formatting difference at all: **the module never validates the format
specification** (`scan_format` only finds its end, `parse_spec` takes any character as the type), so
`info("{:s}", 42)` compiles and is silently ignored, where `std::format` and fmt reject it at
compile time. That is **DEF-5**, and fixing it means moving the check from `format_matches<arg_count>`
(which knows only the argument *count*) into `format_string`'s constructor (which knows their
*types*).

**The dialect difference is structural**, not a bug in one place: fmt cannot enter the module
interface, so the module's own dialect stays as long as the module formats inside its own interface.
Making the two paths agree means moving the formatting out of the module interface - the plan's last
step. So the decision is **FMT-14**: document the dialect, validate the specification, or move the
formatting.

**Part 14 - the four questions that needed no compile.**

- **Intel's `stdx` is fmt-based.** `STDX_FMT_COMPILE` *is* `FMT_COMPILE`, and `stdx::ct_format`'s
  `perform_format` is a `consteval` that calls `fmt::format_to` into a fixed-size `ct_string`.
  **Intel did not write a constexpr formatter - they used fmt's one**, which independently
  corroborates the fmt decision. (Intel's *own* hand-rolled one is the freestanding mini-formatter,
  and it `static_assert`s what it does not support - the opposite of the module's scanner.)
- **The logger's lifetime is sound**, with one hazard in the public API: quill says `flush_log()`
  must not be called from a static object's destructor (`quill/Logger.h:613`), and the project's
  public `flush()` does not say so (**QUIL-9**). The backend is stopped at exit through quill's own
  `atexit` handler, the level threshold is atomic, and the project's level round-trip is exact.
- **`ut`'s module variant is reachable and still not usable.** Upstream ships the `import std`
  gate table, and its CMake 4.4 UUID is the one this project already uses - so CMake was never the
  obstacle. But `import ut;` puts the `std` module in the test translation unit, and GCC 16 then
  collides with the standard headers `tests/logging_test.cpp` needs.
- **The upstream watch:** fmt#3403 is **closed as completed** (2023-06-17) - the fmt side of the
  watch list is resolved; llvm#171292 is still open, and LWG4531 (WP, Brno June 2026) has settled
  the macro values; llvm#63939 and #62258 have not moved.

**The root README was corrected** in the same commit: the global-module-fragment rationale (the
observed failure mode, not the standard's rule), the "the two paths share the same threading"
claim (only the catalog path formats on the backend thread), the `ut` port's reason, and a pointer
to the audit.

## What part 15 changed

**BUILD-6 is answered: the catalog IDs are the same under both compilers - and not by luck.** All
nine catalogs on disk (two compilers, four build configurations, two build times) are
**byte-identical**, and the mechanism says they have to be:

- the message is carried in the message's **type** - `sc::string<char...>` - not in the mangling's
  structure (`log_binary/catalog/catalog.hpp:7`);
- the tool reconstructs the message **text** from the character codes
  (`gen_str_catalog.py:175-177`);
- the messages are sorted **by that text** (`:228-229`) and the IDs are handed out in that order
  (`:300-304`).

So **the ID is the message's rank among the messages, in text order** - and the mangling never
enters the calculation. The one part of the symbol that could have carried a compiler-dependent
type name is `sc::args<...>`, and cib's encoder only accepts **integral, float and enum** types
(`arguments.hpp:31-33`), which both compilers spell the same way. The **link** is the backstop: a
message the tool dropped or misread leaves an undefined `catalog<...>` symbol.

**But the corollary is a new defect: the IDs are not stable across releases.** Because the ID is
the rank in text order, adding a message that sorts first renumbers every message after it - and
the XML is **MIPI Sys-T deployment collateral**, where the IDs are the wire identifiers. The tool
has the mechanism that prevents this (`gen_str_catalog(STABLE_JSON ...)` → `--stable_json` →
`read_stable` → `assign_ids`), and `cmake/catalog.cmake` does not use it: the flag reaches argparse
with an empty list, so **every regeneration renumbers from scratch**. That is **DEF-6**, and where
the stable catalog file should live is **BUILD-7** - an owner decision, with the recommendation
being a committed file (a build-tree file does not survive a clean build, so it would not fix
anything).

**Two new owner decisions** came out of it: **BUILD-7** (where the stable catalog lives) and
**BUILD-8** (whether the build should check the catalog's message set against the call sites - the
link catches a dropped message today, but only a build that links).

## What part 16 changed

**Part 16 - the root README, checked line by line.** Every factual claim in `README.md` was checked
against the file it describes. Four were wrong; the README is now corrected.

- **The global-module-fragment claim was in the README three times**, and part 13's fix had
  corrected only two of them. The third is in the Logging section's macro paragraph. All three now
  say what the standard says and what the compilers do (the collision is an **implementation
  deficiency**, not the rule - [module.global.frag]/1, [std.modules]/4-5). The two **source**
  comments are still deferred.
- **"does not match the arguments"** was ambiguous in the wrong direction: the module checks the
  **number** of arguments, not their types. The README now says "the **number** of arguments" and
  points at DEF-5.
- **The catalog JSON block was abridged without saying so.** It is now the **generated file
  verbatim** (the only difference is the trailing newline a fenced block needs).
- **The "Without vcpkg" command could not work.** Overriding the toolchain also removes vcpkg's
  **search path** - vcpkg's own toolchain is what puts the installed tree on `CMAKE_PREFIX_PATH`
  (`vcpkg.cmake:452`) - so `find_package(intel-cib CONFIG REQUIRED)` had nowhere to look. The
  command now passes the prefix path, with a note about which triplet to use.

**The README's main build claim holds, and now rests on a check.** The committed tree has **never
been rebuilt**: the formatter-conformance commit `61ba2da` landed **90 seconds after** the last
build. But the change is **provably semantics-preserving** - the eight files it touched were
compared by **token stream** (comments, string and character literals, raw string literals and
escapes recognised), and all eight are **identical**:

| File | tokens | identical? |
|---|---|---|
| `include/cpp-core/logging/cib_quill.hpp` | 1106 | **yes** |
| `include/cpp-core/logging/internal.hpp` | 148 | **yes** |
| `include/cpp-core/logging/quill_logger.hpp` | 41 | **yes** |
| `modules/logging/format.hpp` | 3939 | **yes** |
| `modules/logging/logging.cppm` | 838 | **yes** |
| `src/logging/quill_logger.cpp` | 1001 | **yes** |
| `src/reflection_demo.cpp` | 95 | **yes** |
| `tests/logging_test.cpp` | 1233 | **yes** |

Whitespace outside literals is not significant in C++, and the punctuators that *are* significant
inside macros - `#` and `##` - are tokens, so they are compared too. **The committed tree is the
same program as the tree that built and passed the tests.** Everything else in the README checks
out - the module's API list, the verbatim `format_string<>` signature, the IWYU scope table, the
preset, sanitizer, hardening, triplet and port claims - and **all five overlay ports are pinned to
their upstream HEAD** (checked against the GitHub API on 2026-11-12).

**The fmt sources are now vendored** - the last major upstream dependency without a local copy -
and the vendoring turned up something worth recording: **the installed fmt is not pristine upstream
12.2.1**. vcpkg applies a patch of its own to the release tarball, backporting upstream PR **#4813**
("Fix fallback uint128 bitwise not") - three lines in `include/fmt/format.h`. So **every `format.h`
line number after 328 is three higher in the installed file than in pristine upstream**, and the
audit's citations (which are to the installed file) would have been three lines out for a reviewer
checking against upstream. The patch is vendored beside the header, the three-line insertion was
verified by applying it to a pristine upstream checkout, and the result is byte-identical to the
installed header.

| file | provenance | git blob |
|---|---|---|
| `fmt/base.h` | byte-identical to upstream 12.2.1 | `9df283418079f4745f2120e8647a447f4836ac30` |
| `fmt/compile.h` | byte-identical to upstream 12.2.1 | `f05d8426c680eada6bb1270c009a6e06038096f6` |
| `fmt/format.h` | upstream 12.2.1 **+ the #4813 backport** | `0bff24a6bfec476daa63976db457b439431e58ac` |
| `fmt/LICENSE` | byte-identical to upstream 12.2.1 | `795fdaec8f2ce6fcc97bbb15d1a6ac073af7bd17` |

Every fmt citation in the audit was checked against the vendored files: `base.h:1440`,
`base.h:1473-1477`, `base.h:1503-1512`, `base.h:1530-1558`, `format.h:2991-3005`, `format.h:3496`,
`compile.h:55-60`, `compile.h:565-578` and `compile.h:594` - **all of them resolve to what the audit
says they resolve to**.

**Nothing new was built, configured, run or regenerated.** Part 16 closes the last of the
no-compile research: what remains is the implementation (parked) and the owner decisions.

## What part 17 changed

**Part 17 - the decisions, collected.** The audit has **80 open items** (83 when part 17 was
written; part 18 then answered three of them). Sixty-seven are
settled by a compile, a run or a preprocessor pass - they are *questions*, and they unblock the
moment the build lane reopens. **Thirteen are decisions**, because the answer is a judgement about
what the project should be rather than a fact about the world. They were scattered across
`open-items.md`; part 17 gathers them into one sheet, with a recommendation for each.

**Four of them gate the implementation:**

| # | Decision | Recommendation |
|---|---|---|
| **FMT-14** | the module path's format dialect | (a) document it now, (b) validate it if the API is public, (c) move it only if the Codec experiment works |
| **TOOL-13** | `.cmake-format.yaml` or `.cmake-format.json` | **JSON** - YAML needs a new dependency *and* a pinning decision, and the project has neither |
| **TOOL-14** | a one-shot `cmake-format -i` sweep? | **accept the canonical layout** - the project's configuration should describe the project, not reconstruct a past hand-layout |
| **BUILD-7** | where the stable catalog lives | **a committed file** - the IDs are wire identifiers, and a wire identifier that changes when a message is added is not an identifier |

**The other nine shape the project but do not gate it:** `BUILD-1` (warning flags - the
recommendation is `-Wall -Wextra` now and the rest measured later, so the compiler's warnings and
clang-tidy's checks do not arrive in the same diff), `BUILD-2` (consumability - defer until the API
stops moving), `BUILD-3` (the public header surface - make `quill_logger.hpp` private, which is
what its own comment already says), `BUILD-4` (`clang23` - keep the acceptance branch, add no
preset, because Homebrew's libc++ has no `<meta>` and it cannot build the project), `BUILD-5` (CI
- none yet; there is no remote, so CI cannot run), `BUILD-8` (a catalog message-set check - yes,
as part of the coverage work), `QUIL-9` (`flush()` - document quill's static-destructor caveat),
`ENV-2` (delete the abandoned `build/coverage-clang/`) and `ENV-3` (`ZAI_API_KEY` - not a cpp-core
decision at all).

**The cheapest path:** if the owner answers only those four, **every one of the plan's ten steps
is unblocked** - and if **FMT-14** is answered **(a)**, then step 7 is *deferred* rather than
blocked, and steps 1-6 and 8-10 proceed without it.

**One correction to a list that was circulating:** **VCPKG-2** (do the overlay ports shadow builtin
vcpkg ports?) is **not** an owner decision - it is a research step, answered by reading the vcpkg
registry at the pinned baseline `245d37306671ea67d8f313081a81aae8079f8916`.

**It was believed to be blocked** only because `$VCPKG_ROOT` here is the vcpkg *tool*, with no
`ports` tree and no `.git`. That is true of the local install and false of the registry: the
registry is a git repository and the baseline is a commit in it, so the reading is done over HTTP
against that commit, without a checkout. The same read answers **VCPKG-1**.

**Both are now answered** (part 18, section 2, and `open-items.md` section 12): the upstream
`quill` port has no external-fmt feature and quill 13.1.0 offers no fmt switch at all, so the two
copies of fmt are structural; and **none** of the five overlay ports shadows a builtin vcpkg port
at the pinned baseline - so all five track upstream rather than the pinned baseline.

## State of the working tree

- Committed and clean.
- `build/coverage-clang/` - an abandoned experiment (clang source-based coverage); the raw-profile
  version mismatch makes it unusable, it can be deleted.

## Open question for the owner (answered, not acted on)

How to set `ZAI_API_KEY` for the `zai-coding-plan` provider was answered: the two saved `Z.AI`
accounts in `opencode auth list` belong to the `zai` integration (the standard API), not to
`zai-coding-plan` (the Coding Plan endpoint), so they do not satisfy it. Either
`opencode service set env ZAI_API_KEY <key>` (stops and restarts the background service) or
`opencode auth login zai-coding-plan` (a saved account, no restart). The local `opencode.json` only
registers `glm-4.7` for that provider; `glm-5.3` and `glm-5.3-flash` are in the catalog and would
have to be added.
