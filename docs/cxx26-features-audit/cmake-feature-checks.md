# Can CMake ask the compiler? Feature checks, CMake 4.5, and the presets

**Date:** 2026-11-13
**Status:** research. Nothing here is applied. The build lane is parked, so no check was run -
this part writes them down, it does not execute them.

**What this part is.** The audit's open list has **70 questions settled by "a compile, a run or a
preprocessor pass"** ([open-items.md](open-items.md)), and 30 of them are classified `compile`
alone. CMake has a facility for exactly that: a check that compiles and links a small program,
records whether it worked, and keeps the answer. This part asks four things:

1. what are those facilities, and what can each one settle;
2. what does a check **see** of this project - and what does it **not**;
3. what did CMake **4.5.0** add, on 2026-11-12, and which of it matters here;
4. what has the project's **preset file** left on the table, and what do the worked examples look
   like for two of the parked questions.

The answer is not "yes, all 30". It is "yes for most of them, and here is exactly where the
facility stops" - and the place it stops is the project's own module and the project's own
reflection flags.

## 1. The short answer

**CMake has the facilities, and they are the right shape for a parked compile question.** A check
is a snippet, a compiler and a cache variable: `check_cxx_source_compiles` compiles a whole program
from a string and stores 1 or 0; `try_compile` builds a source file, or a whole project, and can
build a **module interface unit** in the process; `check_cxx_compiler_flag` asks about a flag;
`CMAKE_CXX_COMPILE_FEATURES` reports what the compiler **claims**.

**But four things are true of every one of them, and they shape what the 30 questions can expect.**

- **A check compiles a snippet, not the project.** The generated program has no access to
  `com.rsm.logging`; the module does not exist at configure time. So no check can answer a question
  whose form is "does this compile against the project's module". `FMT-15` already says so, and it
  is right.
- **The project's reflection flags do not reach a check.** They are deliberately kept out of
  `CMAKE_CXX_FLAGS` (`cmake/toolchains/cpp-core.cmake:94-98`), and they are added instead as a
  directory-scope `add_compile_options()` (`cmake/cpp-core-check.cmake:47-49`) in a file CMake does
  **not** run inside a try_compile project. A reflection check has to pass the flags itself.
- **A check runs once.** Its answer is an INTERNAL cache variable, kept for the life of the build
  tree. Upgrade the compiler under the same preset name and the old answer survives.
- **A check is not a test.** The answer is a cache variable, not a ctest test, so the coverage gate
  ([coverage-gaps.md](coverage-gaps.md)) does not see it, and the 100% rule does not apply to it.

**And one thing the facilities are better at than the audit assumed.** `try_compile` with
`SOURCES_TYPE CXX_MODULE` (CMake 3.28) puts a source into a `FILE_SET` of type `CXX_MODULES` in the
generated project, so a check **can** build a module interface unit and an importer of it. That is
enough to answer `MOD-11`'s question about the *shape* - an importing translation unit that
includes standard headers - even though it cannot answer it about the *project's* module.

## 2. The facilities

| Facility | What it is | Since | The project's use |
|---|---|---|---|
| `check_cxx_source_compiles` | compiles and links a whole program from a string; the answer is a cached boolean | 3.1 | the shape for most of the 30 |
| `check_source_compiles` | the same, for a chosen language, with `SRC_EXT` | 3.19 | only if the extension matters |
| `try_compile` | builds a source file, or a whole project, from the caller's CMake | 3.25 (source form; `SOURCES_TYPE CXX_MODULE` 3.28) | the only one that can build a module unit |
| `check_cxx_compiler_flag` | asks whether the compiler **accepts** a flag | 2.8 | for flag questions, not feature questions |
| `CMAKE_CXX_COMPILE_FEATURES` | the features the compiler **claims** | 3.1; `cxx_std_26` 3.30 | no - it cannot answer a C++26 feature question |
| `check_type_size` | the size of a type or expression, and whether it exists | 2.8; `RESULT_VARIABLE` 4.2 | no use today; it is here because it answers a value |
| `cmake_push_check_state` | saves and restores the `CMAKE_REQUIRED_*` variables around a check | 2.8 | whenever two checks set different flags |

### 2.1 `check_cxx_source_compiles`

```cmake
include(CheckCXXSourceCompiles)
check_cxx_source_compiles(<code> <variable> [FAIL_REGEX <regexes>...])
```

It compiles **and links** the program. `main` is required unless
`CMAKE_TRY_COMPILE_TARGET_TYPE` is `STATIC_LIBRARY`. The result is an INTERNAL cache variable: `1`
on success, empty on failure. It is **cached**, so it runs once per build tree unless the variable
is unset.

Two details are worth knowing, and both come from the module's own source:

- **The check defines `-D<variable>` in the program it compiles.** So the program can be written
  against its own answer - `#ifdef CPP_CORE_HAS_X` - which is how a check's source can be shared
  between the passing and the failing case.
- **`FAIL_REGEX` turns a success into a failure.** The compile is inspected, and if the output
  matches one of the patterns the result is forced to 0. It is the direction that matters when the
  question is "does the compiler *merely warn* about this".

The variables that change how the check runs: `CMAKE_REQUIRED_FLAGS`, `CMAKE_REQUIRED_DEFINITIONS`,
`CMAKE_REQUIRED_INCLUDES`, `CMAKE_REQUIRED_LIBRARIES`, `CMAKE_REQUIRED_LINK_OPTIONS`,
`CMAKE_REQUIRED_LINK_DIRECTORIES`, `CMAKE_REQUIRED_QUIET`, and `CMAKE_TRY_COMPILE_TARGET_TYPE`.

### 2.2 `try_compile`

The source-file signature (3.25) is the one that matters here:

```cmake
try_compile(<resultVar>
            [SOURCES_TYPE <type>]
            {SOURCES <srcfile>...              |
             SOURCE_FROM_CONTENT <name> <cont> |
             SOURCE_FROM_VAR <name> <var>      |
             SOURCE_FROM_FILE <name> <path>    }...
            [LOG_DESCRIPTION <text>] [NO_CACHE] [NO_LOG]
            [CMAKE_FLAGS <flags>...] [COMPILE_DEFINITIONS <defs>...]
            [LINK_OPTIONS <options>...] [LINK_LIBRARIES <libs>...]
            [OUTPUT_VARIABLE <var>] [COPY_FILE <fileName>]
            [<LANG>_STANDARD <std>] [<LANG>_STANDARD_REQUIRED <bool>]
            [<LANG>_EXTENSIONS <bool>])
```

Four options earn their place in a project like this one:

- **`SOURCES_TYPE CXX_MODULE`** (3.28) - the source goes into a `PRIVATE FILE_SET ... TYPE
  CXX_MODULES` in the generated project, so the check builds a real module unit. This is the only
  way a CMake check touches a module.
- **`OUTPUT_VARIABLE`** - the compiler's output, kept. It is how a check reports *why* rather than
  *whether*.
- **`CMAKE_TRY_COMPILE_TARGET_TYPE` = `STATIC_LIBRARY`** - skips the link, which is what a
  compile-only question wants (and the only form that works when the toolchain has no linker).
- **`NO_CACHE`** - keeps the intermediate result out of the cache when the check is a step in a
  larger inspection.

### 2.3 `check_cxx_compiler_flag` and `CMAKE_CXX_COMPILE_FEATURES`

`check_cxx_compiler_flag(<flag> <variable>)` compiles a trivial program **with** the flag and
passes only if the compiler accepts it - with the warnings-as-errors probes that stop a compiler
from silently ignoring a flag it does not know. It answers a question about a **flag**.

`CMAKE_CXX_COMPILE_FEATURES` is a different kind of thing: it is what the compiler **claims**, not
what it was observed to do. `cxx_std_26` (3.30) is the meta-feature, and CMake's own documentation
is careful about it - "it reflects the language support claimed by the compiler, but it does not
necessarily imply complete conformance to that standard". Individual features exist only for
C++98, C++11 and C++14; there are none for C++17 or later. So this cannot answer a C++26 language
question, and it certainly cannot answer a **library** question - which is the one this project
keeps asking ([cxx26-library-availability.md](cxx26-library-availability.md): the libraries are
behind the compilers).

### 2.4 `check_type_size` and `cmake_push_check_state`

`check_type_size(<type> <var> [RESULT_VARIABLE <result>] [BUILTIN_TYPES_ONLY] [LANGUAGE CXX])`
records the **size** in `<var>` and whether it exists in `HAVE_<var>` (or in `RESULT_VARIABLE`,
since 4.2). It is the one facility here that answers a value rather than a yes or no. The project
has no use for it today.

`cmake_push_check_state(RESET)` / `cmake_pop_check_state()` save and restore the `CMAKE_REQUIRED_*`
variables, so one check's flags do not leak into the next. Any block of checks that sets
`CMAKE_REQUIRED_FLAGS` belongs inside them.

## 3. What a check sees of this project, and what it does not

This is the part that is specific to cpp-core, and it decides which of the 30 questions a check can
carry.

**It sees the compiler.** The toolchain already does the work: `CMAKE_TRY_COMPILE_PLATFORM_VARIABLES`
carries `CPP_CORE_COMPILER`, `CPP_CORE_SANITIZER`, `CPP_CORE_HARDENING`, `CPP_CORE_PORT_BUILD` and
`CPP_CORE_EXTRA_CXX_FLAGS` (`cmake/toolchains/cpp-core.cmake:38-45`), and the toolchain file is
re-read inside the check's project. A check therefore knows which of `gcc16`, `clang23` or `p2996`
it is running under, and can name its answer per compiler.

**It sees the flags.** `CMAKE_CXX_FLAGS` is copied into the generated project, so the sanitizer
flags, the hardening macro, `-stdlib=libc++` and `CPP_CORE_EXTRA_CXX_FLAGS` all reach the check
(`cmake/toolchains/cpp-core.cmake:192-196` builds that string).

**It sees the standard.** `CMAKE_CXX_STANDARD 26`, `CMAKE_CXX_STANDARD_REQUIRED ON` and
`CMAKE_CXX_EXTENSIONS OFF` are set by the toolchain (`cmake/toolchains/cpp-core.cmake:88-92`), and
the generated project honours them and sets them as target properties. A check compiles as C++26.

**It does not see the reflection flags.** The toolchain keeps them out of `CMAKE_CXX_FLAGS` for a
reason it states (`cmake/toolchains/cpp-core.cmake:94-98`): GCC 16 refuses `-freflection` below
`-std=c++26`, so a flag in `CMAKE_CXX_FLAGS` breaks every compile that is not C++26 - the vcpkg
port builds, CMake's own compiler checks, and any consumer that forwards `CMAKE_CXX_FLAGS`. They
are added instead by `cmake/cpp-core-check.cmake:47-49`, and that file is reached through
`CMAKE_PROJECT_INCLUDE`. **`CMAKE_PROJECT_INCLUDE` is not among the variables CMake propagates into
a try_compile project** - the list is explicit in CMake's own source, and the project's five
`CMAKE_TRY_COMPILE_PLATFORM_VARIABLES` are the only project-specific entries in it. So:

- the project's compiler **gate** (`cmake/cpp-core-check.cmake:12-44`) does not run inside a check
  either - a check is not protected by the gate that protects the build;
- **a reflection check must pass `-freflection` itself**, through `CMAKE_REQUIRED_FLAGS`. That is a
  real cost for the `REFL-` items and for `FMT-10`/`MAC-1`.

**It does not see the project's headers or the installed ports** unless the check adds them
(`CMAKE_REQUIRED_INCLUDES`), and it cannot import the project's module. `FMT-15` reached the same
conclusion from the other side, and it is the reason the "must not compile" cases need a different
mechanism.

**And the one thing it can do that the audit had not credited.** `SOURCES_TYPE CXX_MODULE` gives a
check a module unit and its importer, both built by the same compiler with the same flags. The
*shape* of the question - an importing translation unit that includes a standard header - is
therefore testable, even when the *specific* module is not.

## 4. The thirty compile questions, and what could answer each

The 30 questions the registry classifies `compile` alone:

| The question | Could a CMake check answer it? | Which facility, and how |
|---|---|---|
| `FMT-1` - does `FMT_STATIC_FORMAT` compile on both toolchains? | **yes** | `check_cxx_source_compiles` with `CMAKE_REQUIRED_INCLUDES` for fmt's headers |
| `FMT-2` - does fmt constant-evaluate floating point? | **yes** | the check's own `static_assert`, so a failure to constant-evaluate is a compile failure |
| `FMT-3` - does `FMT_STATIC_FORMAT` need a `constexpr` `std::string`? | **yes** | two checks: one with the `std::string` form, one without |
| `FMT-4` - can `format.hpp` be `constexpr` wholesale? | **no** | it is the project's own header; a check can compile **a copy** of the pattern, not the header |
| `FMT-5` - does the `static_assert` test pattern work? | **partly** | the shape is checkable; the project's own `format_message` is not |
| `FMT-7` - does `format_to_n` truncate like `snprintf`? | **no** | it is a **run-time** comparison; a check only compiles |
| `FMT-8` - can a custom `fmt::formatter<T>` interoperate with `fmtquill`? | **yes** | a check with `CMAKE_REQUIRED_LIBRARIES` for both libs' targets |
| `FMT-10` / `MAC-1` - does `std::source_location::current()` in a default argument return the caller's location? | **no** | it is a run-time answer; `CheckSourceRuns` or a test |
| `FMT-12` - does `fmt::runtime` exist under that name? | **yes** | a check takes the address of the name |
| `FMT-13` - the authoritative feature-test macro values | **yes** | one `check_cxx_source_compiles` per macro value - **worked example, section 7.1** |
| `MOD-1` - how large is the GCC migration in option (c)? | **no** | a migration, not a question with a boolean answer |
| `MOD-2` - can the type-erasure boundary use a fixed-size representation? | **partly** | the representation compiles or not; the design is a judgement |
| `MOD-3` - does GCC 16 translate an `#include` inside a module unit? | **yes** | `try_compile` with `SOURCES_TYPE CXX_MODULE` |
| `MOD-4` - does GCC 16 reject an importer that includes only `<unistd.h>`? | **yes** | the same, with `<unistd.h>` as the only include; the check's pass/fail **is** the answer |
| `MOD-5` - is `<unistd.h>` in GCC 16's importable-header set? | **yes** | the same shape |
| `MOD-6` - does the failure persist with `--compile-std-module`? | **yes** | the whole-project `try_compile` form, with `CMAKE_FLAGS` carrying the flag |
| `MOD-8` - do quill's, cib's and ut's headers compile after `import std;` on p2996? | **yes** | `try_compile` with `SOURCES_TYPE CXX_MODULE` plus `CMAKE_REQUIRED_INCLUDES` |
| `MOD-10` - does a TU that imports the module and includes `cib_quill.hpp` compile? | **no** | needs the project's module - the check cannot import it |
| `MOD-11` - does the matrix's failure reproduce in the project's configuration? | **partly** | the *shape* is checkable with a throwaway module - **worked example, section 7.2** |
| `QUIL-1` - can a `Codec` push three arguments from one pack element? | **yes** | a check with quill's headers and a `static_assert` on the result |
| `QUIL-2` - which types push into `DynamicFormatArgStore` without a formatter? | **yes** | one check per type, or one check with a `FAIL_REGEX` per rejection |
| `QUIL-4` - does fmt render the whole specification cross-product identically? | **no** | a differential test - it compares **output** |
| `QUIL-5` - can `format_string` hold a compile-time-rewritten template? | **partly** | the shape compiles or not; the project's type is not reachable |
| `QUIL-6` - does the compiler accept a non-terminated `char const[N]` at the `consteval` boundary? | **yes** | a check with the same shape and the project's `consteval` construction copied in |
| `REFL-1` - do the two compilers' `members_of` forms compile the same source? | **yes** | a check per compiler, **with `CMAKE_REQUIRED_FLAGS` carrying `-freflection`** |
| `REFL-2` - are `access::unprivileged()` and `access_context::unchecked()` the same? | **yes** | the same, with one check per spelling |
| `REFL-3` - does `std::meta::exception` throwing work inside `consteval`? | **yes** | the same |
| `REFL-4` / `MAC-3` - does `std::format_string<Args...>` accept the project's format strings? | **no** | the project's own scanner and alias; a literal scan, not a check |

**The tally: about 20 of the 30 are a check's shape, 6 are not, and 4 are partly.** The ones that
are not are not failures of CMake - they are **run-time** questions (`FMT-7`, `FMT-10`, `QUIL-4`),
**design** questions (`MOD-1`, `MOD-2`), or questions about **the project's own module**
(`MOD-10`, `FMT-4`, `REFL-4`).

## 5. What CMake 4.5.0 added

4.5.0 was released on 2026-11-12. Its release notes are long; this section keeps every item, in
the release's own groups, and says which ones touch this project. **The project's minimum is 3.31
(`CMakePresets.json:4-8`), so everything here is available to it.**

### 5.1 The five that matter to this project

**`import std` is now available for all C++20 and later code with `CXX_SCAN_FOR_MODULES` enabled.**
This is the headline for part 4. The project's module rule is about GCC 16's mixing deficiency
([import-std.md](import-std.md)), and `MOD-1` through `MOD-6` are the price of the migration. A
CMake that can build `import std` for any C++20 target is what makes option (c) a configuration
change rather than a build-system project - **and `CMAKE_CXX_SCAN_FOR_MODULES` is already in the
list of variables CMake propagates into a try_compile project**, so a check can build an `import
std` translation unit.

**`CMAKE_CXX_STDLIB_MODULES_JSON`.** A variable to set the path to the `import std` metadata file
instead of letting the compiler discover it. It is also propagated into try_compile projects. For
`MOD-6` - "does the failure persist when `--compile-std-module` has actually built the header
unit?" - this is the knob that says *which* metadata file the build used, so the experiment can be
described exactly rather than inferred.

**`install(TARGETS)` no longer requires a `LIBRARY DESTINATION` for module libraries.** `BUILD-2`
(the install/export design) writes `install(TARGETS ... FILE_SET CXX_MODULES ...)`, and a module
library's destination was one of the loose ends. It now has a default that follows the platform.

**`install_prep/all`, `install_prep/<component>`, `test_prep/all` and `test_prep/<test-name>`.**
New convenience targets, on by default, that build everything an install or a test needs - and the
release notes call out that this **includes the targets that produce installed C++ module BMIs and
module export metadata**. That is precisely the dependency `BUILD-2` would otherwise have to
hand-write.

**A new diagnostic, `CMD_NON_TARGET_DIRECTIVE`.** It fires on commands that affect the directory
scope when a comparable target-specific command exists - and the project has exactly one:
`add_compile_options()` in `cmake/cpp-core-check.cmake:47-49`, which adds the reflection flags for
every target in the directory because they cannot go in `CMAKE_CXX_FLAGS`. The diagnostic is
**controllable from the presets**, in `configurePresets.warnings` and `configurePresets.errors`
(schema version 12 renamed `dev` to `author`; 4.5 added `nonTargetDirective` and `strict`). So the
project can make the new diagnostic an **error** where it wants to enforce target scope, and the
one place it does not want that is the file that has no choice.

### 5.2 The rest of the release, and whether it touches cpp-core

| 4.5 feature | Touches cpp-core? |
|---|---|
| `CMD_NON_TARGET_DIRECTIVE`, `CMD_STRICT` diagnostics | **yes** - see above |
| Schema version 13; the `${configurePresetName}` macro | **yes** - section 6 |
| `CMAKE_CXX_STDLIB_MODULES_JSON` | **yes** - `MOD-6`, above |
| `import std` for all C++20+ with `CXX_SCAN_FOR_MODULES` | **yes** - part 4 |
| `install(TARGETS)` destination default for module libraries | **yes** - `BUILD-2` |
| `install_prep/*`, `test_prep/*` targets | **yes** - `BUILD-2` |
| `install(SBOM)` / `export(SBOM)`, `CMAKE_INSTALL_SBOM_FORMATS` | later - a released library wants an SBOM; this project has no release |
| `FILE_SET_TYPES`, `FILE_SETS_<TYPE>`, `INTERFACE_FILE_SETS_<TYPE>` | **yes, small** - the module is the target's whole interface, so a property query would replace reading the CMakeLists by hand |
| The `LANGUAGE` and `SOURCE_GROUP` file set properties | marginal - `format.hpp` is a `PRIVATE` source, not a file set |
| `install()`/`export()` accept alias targets; `add_dependencies()` accepts them; the `target_*` commands accept them | unblocks a naming detail: `cpp-core::logging` is an alias, and install/export of an alias was previously a rewrite |
| `cmake_language(PRINT_VARIABLES/PRINT_TARGETS/PRINT_PROPERTIES)` | **yes, small** - and it deprecates `CMakePrintHelpers` |
| `add_custom_rule()` | no - the catalog tooling uses explicit targets |
| `ctest --out-of-date` | **yes** - `TOOL-9`/`TOOL-8` want a cheap "rerun only what changed" |
| `discover_tests(... BUILD_DEPENDS ...)` | marginal - the suite is one binary |
| `install(FILES/PROGRAMS/DIRECTORY/SCRIPT/CODE ... BUILD_DEPENDS ...)` | **yes, in `BUILD-2`** |
| `install(TARGETS ... RUNTIME_DEPENDENCY_TARGETS ...)` | no - no shared libraries built here |
| `CMAKE_COMPILE_WRAPPER_<NAME>` / `CMAKE_LINK_WRAPPER_<NAME>` | **yes** - a sanctioned way to wrap the compile line, which is what a coverage or IWYU pass wants (part 3) |
| `$<ARGS>`, `$<DIRECTORY_PROPERTY>`, `$<GLOBAL_PROPERTY>`, `$<RULE_PROPERTY>` | no - nothing to build with them |
| `LIST` `PREDICATE`/`REGEX`/`COMPARATOR`/`APPLY` | no - the project's lists are small and static |
| `string(JSON ... ARRAY_SPLIT)` | **yes, small** - the catalog tooling reads and writes JSON; a single-parse split is the linear-time form |
| `cmake --install` fails when an install script fails | **yes** - it is the `BUILD-2` failure mode |
| `cmake --build` groups each recipe's parallel output | **yes, ergonomic** - vcpkg port builds are noisy |
| `cmake --list-presets=defined` and friends | **yes** - section 6 |
| `CMAKE_SYSTEM_ENVIRONMENT_ID`, `CMAKE_SYSTEM_ENVIRONMENT_ACTION` | **yes** - it is the answer to a **stale check answer**: the hint that `--fresh` is needed |
| `CMAKE_DIAGNOSTIC()`; `-Wnon-target-directive`, `-Wstrict` | **yes** - the presets' `warnings` object |
| File-based API `interfaceIncludes`; codemodel 2.12 | **no** - no IDE integration |
| Instrumentation 1.2, `interruptSignal` | **no** - the project runs no job server |
| DPC++ (`DPClang`) compiler id | **no** - two compilers, neither DPC++ |
| CPack APK generator | no |
| AUTOMOC on module file sets; Qt 6.13 | no |
| `FindCUDAToolkit` namespace targets; `FindDoxygen` `USES_TERMINAL`; `FindPython*` emulator overrides | no |
| Fortran intrinsic modules under Ninja; Swift module name under Xcode; `XCODE_EMBED_<type>` genexes | no |
| `TEST_INCLUDE_FILES` generator expressions | marginal - the coverage gate's scripts could be per-config |
| `CMAKE_TEST_BUILD_DEPENDS` (the variable) no longer honoured; `CMAKE_SKIP_TEST_PREP_TARGETS` | **yes** - it is the switch for the new prep targets |
| `ALIASED_TARGET` is read-only | no |
| `cmake_path(IS_PREFIX)` and empty paths; `if(PATH_IS_PREFIX)` | no |
| `install_files()`, `install_programs()`, `install_targets()`, `make_directory()`, `remove()`, `subdirs()`, `write_file()` now emit deprecation diagnostics | **nothing to do** - the project uses none of them (checked: no matches in `cmake/`) |
| `CMakePrintHelpers`'s two commands deprecated | **nothing to do** - not used |
| The Visual Studio 14 2015 generator removed | no |
| `cmake_host_system_information()` `DISTRIB_*` reads os-release | no |

**The three deprecated commands to check before reopening.** The project does not use
`install_files()`, `install_programs()` or `install_targets()`, and it does not use
`make_directory()`, `remove()`, `subdirs()` or `write_file()` either - the only `add_subdirectory`
is in `cmake/dev-mode.cmake:7`, which is not one of the deprecated forms. So 4.5's deprecation
diagnostics have nothing to say about this tree today. **`BUILD-2` is the one place that could
change that**, and it is a new `install()` anyway.

## 6. The presets: what the project has, and what it has not used

Both preset files are at **schema version 10** (`CMakePresets.json:2` and
`cmake/presets/cpp-core.json:2`), which is CMake 3.31 - the project's own minimum. CMake 4.5
supports **version 13**, and master is already at 14. The project uses configure, build, test and
workflow presets, a hidden base preset per compiler and per configuration, per-preset binary
directories, `$comment` throughout, and `testPresets.execution.noTestsAction` plus the sanitizer
environment. That is a competent file. What it has **not** used:

| Field | Since | What it would buy here |
|---|---|---|
| `$schema` at the root | 8 | editor validation of the presets - one line, and the file currently has none |
| `condition` | 3 | hiding a preset whose compiler is absent; **4.5's `--list-presets=defined` is the better answer** - it lists the preset and explains why it is unavailable |
| `configurePresets.trace` | 7 | a trace of what the configure did - the tool for a misbehaving **check** |
| `configurePresets.warnings` / `errors` | 10 / 12 | **the home of 4.5's `nonTargetDirective` and `strict`** |
| `configurePresets.installDir` | 3 | `BUILD-2`'s install tree |
| `packagePresets` | 6 | nothing yet - packaging is not installing, and the project distributes no binaries |
| `buildPresets.resolvePackageReferences` | 4 | nothing yet - no `FetchContent` |
| `testPresets.output.testOutputTruncation` | 5 | a coverage run's long output |
| `testPresets.output.outputJUnitFile` | 6 | **the artifact a CI would consume** - the concrete shape of `BUILD-5` |
| `testPresets.execution.jobs` (empty string) | 11 | parallel tests - one binary today, but the coverage sweep is per file |
| `testPassthroughArguments` | 12 | **the "must not compile" harness** (`FMT-15`) forwards the source to test |
| `${configurePresetName}` | 13 (4.5) | one place to derive the triplet from the compiler preset, instead of repeating it per configuration |
| `workflowPresets` steps for a check | 6 | a `configure`-only workflow for the feature checks, so they can run without a build |

**And one thing 4.5 changed about the *listing* rather than the schema.**
`cmake --list-presets=defined` prints every non-hidden preset **and explains why an unavailable one
cannot be used**, and a build, test or package preset whose configure preset is unavailable is now
reported as unavailable too. The project's `p2996-*` presets are listed on a machine without
clang-p2996, and today the user finds out at configure time. This makes the answer a query.

## 7. Two worked examples

Both are written as they would go into a `cmake/feature-checks.cmake`, which does not exist. They
are **designs**, not working CMake - the lane is parked and nothing here was run.

### 7.1 `FMT-13` - the authoritative feature-test macro values

**The question.** Part 11 reported the feature-test macros by *scanning the headers*, and it could
not do better: both libstdc++ and libc++ define their macros inside per-standard-version branches,
and a text scan cannot pick the branch the compiler takes. `FMT-13` asks for the authoritative
values, which needs the preprocessor.

**The shape.** One `check_cxx_source_compiles` per value the project cares about. The check
**passes only when the macro has the expected value**, so the answer is the cache variable itself -
and because the variable name carries the value, the configure log reads as a table.

```cmake
include(CheckCXXSourceCompiles)

# The project compiles as C++26 (the toolchain sets CMAKE_CXX_STANDARD 26), so these
# checks see the C++26 branch of each library's <version>.
check_cxx_source_compiles([[
  #include <version>
  #if !defined(__cpp_lib_format)
  #  error "the standard library does not declare __cpp_lib_format"
  #elif __cpp_lib_format != 201907L
  #  error "unexpected __cpp_lib_format"
  #endif
  int main() { return 0; }
]] CPP_CORE_LIB_FORMAT_201907L)
```

Three properties make this the right instrument:

- **the expected value is written down**, so the check is a claim and its failure is a diagnosis,
  not a measurement;
- **the answer is per compiler**, because the presets configure one compiler per build tree and the
  cache variable lives in that tree;
- **`FAIL_REGEX` is the guard** for the case that matters here - a macro that is *undefined* makes
  `#elif` read it as 0, which fails the check anyway, but the compiler may **warn** about an
  unknown macro without failing. A `FAIL_REGEX` on the warning keeps a warning from being read as
  a pass.

**And the second phase is the one that is easy to miss.** Before the expected values can be
written down, they have to be *read*. The trick is the check's own `-D<variable>`: a probe program
whose only job is to fail, with the value in the diagnostic, and `try_compile(...
OUTPUT_VARIABLE ...)` to keep it:

```cmake
# A probe that cannot pass: it fails on purpose, and its message carries the value.
# The compile "fails", which is the point - OUTPUT_VARIABLE keeps the diagnostic.
try_compile(_cpp_core_probe
  SOURCE_FROM_CONTENT "probe.cxx" [=[
    #define STR2(x) #x
    #define STR(x) STR2(x)
    #include <version>
    static_assert(false, "value=" STR(__cpp_lib_format));
  ]=]
  OUTPUT_VARIABLE CPP_CORE_PROBE_OUTPUT)
```

Both compilers print the stringified expansion in the `static_assert` message, so the diagnostic
contains `value=201907L` and the value is read rather than guessed. It is a preprocessor pass run
through CMake instead of by hand - which is exactly what the open item asks for, and it lands in
the configure log in place of a scratch translation unit no one keeps.

### 7.2 `MOD-11` - does the matrix's failure reproduce in the project's configuration?

**The question.** `MOD-11` is the one measurement that decides the price of `import std;`. The
audit's matrix was measured with `-fmodules`; the project's GCC 16 commands use `-fmodules-ts`, and
`tests/logging_test.cpp` imports the module **and** includes `<cstdio>`, `<string>` and
`<unistd.h>` - the shape the matrix says fails - and it builds. So *"option (c) is blocked on GCC
16 today"* is not established for this project.

**Why a plain check cannot answer it, and what can.** The question is about the project's own
module, and a check cannot import it. But the matrix's claim is about a **shape**, not about this
module: *an importing translation unit that includes a standard header*. A throwaway module
reproduces that shape exactly, and `try_compile` with `SOURCES_TYPE CXX_MODULE` builds both units
in one generated project:

```cmake
# The shape the matrix says fails: an importing TU that includes a standard header.
# The module is a throwaway - the question is about the shape, not about our module.
try_compile(CPP_CORE_GCC16_MIXES
  SOURCES_TYPE CXX_MODULE
      SOURCE_FROM_CONTENT "probe.cppm" [=[
        export module probe;
        export int answer() { return 42; }
      ]=]
  SOURCES_TYPE NORMAL
      SOURCE_FROM_CONTENT "main.cxx" [=[
        import probe;
        #include <cstdio>
        #include <string>
        int main() { return answer() == 42 ? 0 : 1; }
      ]=]
  LOG_DESCRIPTION "MOD-11: an importing TU that includes standard headers"
  OUTPUT_VARIABLE CPP_CORE_GCC16_MIXES_OUTPUT)
```

**What the check gets for free, and what it does not.** The generated project calls `project()`
with the C++ language, so it re-reads CMake's own `GNU-CXX.cmake` and gets **the same
`-fmodules-ts` and `-fmodule-mapper` dialect the project uses** - the variable that matters,
`CMAKE_CXX_SCAN_FOR_MODULES`, is one of the ones CMake propagates into a check. It also gets
`CMAKE_CXX_STANDARD 26` and the sanitizer and hardening flags. It does **not** get
`-freflection` - the reflection flags are a directory-scope directive in a file a check never runs

- which is harmless here, because the probe uses no reflection, and is exactly why a `REFL-` check
would have to set `CMAKE_REQUIRED_FLAGS` by hand.

**What each outcome means.**

- **the check fails** - the shape reproduces, and the project's build is the anomaly. The next
  question is why: the global module fragment, or a flag, or a GCC bug that the project's module
  happens to dodge.
- **the check passes** - the shape is fine under the project's dialect, so the matrix's
  `-fmodules` result does not transfer, and `MOD-11` is answered "no, it does not reproduce" -
  which is what the audit's part 4 suspects and could not prove.

Either way the answer is a cache variable with the compiler's output beside it, and it is
re-measured in every build tree rather than remembered from a scratch file.

## 8. The honest limits, collected

1. **A snippet, not the project.** No check can import `com.rsm.logging`, so `MOD-10`, `FMT-4` and
   `REFL-4` are outside a check's reach, and `FMT-15`'s "must not compile" cases stay with the
   `compile_commands.json` harness it proposes.
2. **The reflection flags are the project's own gap.** They are outside `CMAKE_CXX_FLAGS` and
   outside the file a check runs, so every `REFL-` check carries `CMAKE_REQUIRED_FLAGS` by hand.
   That is a cost, and it is the price of the toolchain's (correct) decision at
   `cmake/toolchains/cpp-core.cmake:94-98`.
3. **The check is cached, and its answer can outlive its compiler.** `CMAKE_SYSTEM_ENVIRONMENT_ID`
   and `--fresh`, new in 4.5, are the answer; a check whose answer is load-bearing should be
   re-run when the environment changes.
4. **A run-time question is not a compile-time question.** `FMT-7`, `FMT-10`, `QUIL-4` and
   `MAC-1` need `CheckSourceRuns` or a real test, not a check.
5. **A check is not coverage.** The answer is a cache variable, so the 100% rule and the coverage
   gate do not apply, and the checks cannot be counted as tests.
6. **The facilities are not a substitute for the lane.** Every one of them needs the compiler -
   which is the thing the lane is parked on.

## 9. What this changes for the plan

- **The 30 `compile` questions get a home.** About 20 of them are a check's shape, and the home is
  a `cmake/feature-checks.cmake` that runs at configure time. The audit's "one scratch translation
  unit" answer is the same experiment with no record; the check leaves a cache variable, a
  configure-log entry and a per-compiler name.
- **`MOD-11` gets a decisive experiment.** The throwaway-module check in section 7.2 answers the
  shape question under the project's own dialect, which is more than the matrix can do.
- **`FMT-13` gets a preprocessor pass that runs itself.** The probe in section 7.1 reads the values
  through CMake, and the pinning phase turns them into claims.
- **`BUILD-2` gets cheaper.** CMake 4.5 supplies three of its loose ends: the module library's
  destination default, the `install_prep/*` targets, and `install()`'s `BUILD_DEPENDS`.
- **The presets get a small list.** `$schema`, a `warnings` object carrying 4.5's
  `nonTargetDirective` as an error everywhere except the one file that cannot comply, and
  `testPassthroughArguments` for the `FMT-15` harness.
- **And it adds one decision**, which is section 10.

## 10. The new open question

**`BUILD-9` - should the build gain a feature-check gate?** The three readings:

- **(a) yes, a gate** - a `cmake/feature-checks.cmake` with one check per compile-bearing open
  item, run at configure time on every preset. The answers become cache variables, re-measured per
  compiler and per build tree, and the audit's 30 items become a machine-readable table. The cost
  is a configure-time check that can fail on a compiler the project does not support, and a set of
  one-shot answers that go stale.
- **(b) no - a scratch translation unit per item, on demand** - the answer stays a note in the
  audit and the experiment stays in the developer's hands. Cheap now, and nothing is re-measured.
- **(c) only where the answer gates a code path** - a check for the questions whose answer changes
  what the build does (`HAVE_REFLECTION`, the module dialect, an `import std` capability), and a
  **test** for the rest, which are measurements.

**The recommendation is (c).** A check's answer is a cache variable, and a cache variable is worth
having when something branches on it; for the questions whose answer is only a fact about the
world, the coverage gate is already the place where facts about the code are asserted, and 100% is
already the bar. **(c)** also keeps the one-shot-answer problem where it is harmless: a gating
check's staleness shows up as a build that does not take a code path it should.

## 11. The method

**Read, not run.** No build, no compiler, no CMake, no preset. The CMake facilities are described
from CMake 4.5.0's own release notes and from its command, module, variable and property
documentation, and the behaviour of `try_compile` inside a project - which variables it propagates
and which it does not - is read from CMake's own `cmCoreTryCompile.cxx` rather than inferred. The
project's side is read from its own files, and every claim about them carries a line number.

**Where the two meet.** The one fact this part could not have got from either side alone is that
`CMAKE_PROJECT_INCLUDE` is not propagated into a try_compile project, and therefore that the
project's compiler gate and its reflection flags do not run inside a check. It comes from reading
the list in the CMake source against the project's own toolchain comment - and it is the fact that
decides which `REFL-` questions a check can carry.

**What this part does not do.** It does not write `cmake/feature-checks.cmake`; that is `BUILD-9`'s
answer. It does not change a preset; the preset list in section 6 is the input to that decision.
And it does not settle a single one of the 30 questions - it says **how** each one would be
settled, which is what the audit can do while the lane is parked.
