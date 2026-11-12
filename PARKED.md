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
- The features audit, in ten parts: `3d7e865`, `15be31c`, `0e414de`, plus the parts written since
  (reflection, macro reduction, fmt and `constexpr`, the consolidated open-items list).
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
   namespace `fmtquill`. One line.
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
them: 3 defects, 12 fmt/`constexpr` questions, 8 quill questions, 16 tooling questions, 9
`import std;` questions, 4 reflection questions, 3 macro questions, 10 coverage to-dos and 3
environment items - each with what settles it, plus a table of the questions that are **not** open
because they have already been answered.

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
