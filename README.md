# cpp-core

A collection of modular C++26 libraries. Every library is a C++ module; every namespace starts
with `com::rsm`. The build is driven by CMake presets and vcpkg (manifest mode with overlay
ports), and the code uses C++26 static reflection (P2996).

## Layout

| Path | What it is |
|---|---|
| `modules/logging/` | The `com.rsm.logging` module: the logging library's public interface. |
| `include/cpp-core/logging/` | The headers that the module's implementation and the cib path share. |
| `src/` | The application: the CIB demo (`app.cpp`), the reflection demo (`reflection_demo.cpp`) and the quill logger (`logging/quill_logger.cpp`). |
| `tests/` | The tests, written with [ut](https://github.com/stephenberry/ut). |
| `cmake/` | The toolchain, the presets, the catalog and the include-what-you-use integration. |
| `ports/` | The vcpkg overlay ports. |
| `docs/` | The research: the [C++26 and third-party features audit](docs/cxx26-features-audit/README.md), the ASan leak-check analysis and the module source-location study. |

A new library is a new directory under `modules/`, with a `<name>.cppm` interface unit and a
`CMakeLists.txt` that declares it as a `CXX_MODULES` file set:

```cmake
add_library(cpp-core-<name> STATIC)
add_library(cpp-core::<name> ALIAS cpp-core-<name>)
target_sources(cpp-core-<name> PUBLIC FILE_SET CXX_MODULES FILES <name>.cppm)
```

## Compilers

| Preset prefix | Compiler | Reflection flags |
|---|---|---|
| `gcc16-*` | GCC 16.2 (`g++-16` / `gcc-16`, Homebrew, libstdc++) | `-freflection` |
| `p2996-*` | clang-p2996 (bloomberg/clang-p2996, libc++) | `-freflection -fexpansion-statements -fannotation-attributes` |

Both compilers build and pass the tests. The logging module's interface is deliberately free of
the standard library: on both compilers today, a standard header in the module's global module
fragment collides with the standard headers of the translation units that import it (see
[Logging](#logging)). That collision is an implementation deficiency rather than the standard's
rule — the C++26 text requires implementations to merge `#include` and `import` without conflicting
attachments — so the constraint may become removable when the compilers are fixed.

## Build

```sh
cmake --workflow --preset gcc16-release    # configure + build + test
cmake --workflow --preset p2996-debug
cmake --list-presets                       # all presets
```

There is one workflow per compiler and configuration; each has configure, build, test and
workflow presets of the same name. Every build directory is `build/<preset>`.

| Compiler | debug | release | asan | tsan | iwyu |
|---|---|---|---|---|---|
| GCC 16.2 (`-freflection`) | `gcc16-debug` | `gcc16-release` | `gcc16-asan` | none on macOS (no GCC TSan runtime) | none |
| clang-p2996 (libc++, reflection) | `p2996-debug` | `p2996-release` | `p2996-asan` | `p2996-tsan` | `p2996-iwyu` |

- **release:** `Release`, standard library hardening off.
- **debug:** `Debug`, libc++ hardening set to `debug`. On GCC this is `_GLIBCXX_ASSERTIONS`.
- **asan:** `debug` plus AddressSanitizer and UBSan (`-fno-sanitize-recover`, so UB fails the test), with vcpkg's libraries built the same way (`-asan` triplets). Leak checking is on for clang-p2996 and off for GCC 16.2, whose LeakSanitizer deadlocks at exit on macOS (see [Leak checking](#leak-checking)).
- **tsan:** `debug` plus ThreadSanitizer, with vcpkg's libraries built with TSan too. TSan cannot share a build with ASan, hence a separate preset.
- **iwyu:** `debug` plus the include-what-you-use checks (see [Include-what-you-use](#include-what-you-use)).

## Leak checking

The `p2996-asan` preset runs with `detect_leaks=1` and
`LSAN_OPTIONS=suppressions=${sourceDir}/cmake/lsan.supp`. The suppressions are the allocations that
macOS itself makes and that no program can free:

| suppression | what it is |
|---|---|
| `leak:libobjc` | the Objective-C runtime's class initialization |
| `leak:libdyld`, `leak:_dyld_shared_cache_iterate_text` | dyld's thread-local storage, allocated the first time any `thread_local` is used |
| `leak:snprintf`, `leak:_vfprintf` | the buffer that Apple's libc uses to format a floating-point number |

Each entry matches only the leaks whose allocation stack passes through that platform frame, so a
leak in our own code is still reported: a deliberate 1234 byte leak is still reported with this
file in place.

The `gcc16-asan` preset runs with `detect_leaks=0`: GCC 16.2's LeakSanitizer deadlocks on macOS.
At exit it stops the world, and its helper thread then blocks on ASan's own allocator semaphore
while the main thread waits for that helper, so the process hangs - in a two-line program as well,
not only in ours. No option avoids it (`use_stacks=0`, an early explicit leak check, pre-warming
dyld's shared-cache walk), and GCC's and LLVM's Darwin stop-the-world sources are identical, so
there is no upstream fix to wait for.

Run the tests through the presets, from the repository root:

```sh
ctest --preset p2996-asan               # the tests, with the options above
cmake --workflow --preset p2996-asan    # configure + build + test
```

The sanitizer options live in the test presets, so they apply only when the tests are run through
one. A bare `ctest` in the build directory, or the test binary run directly, does not get them: the
leak check then falls back to the platform default, which is off on macOS, so a leak would not be
reported. `ctest --preset` has to be run from the repository root, because CMake reads
`CMakePresets.json` from the current directory.

The full analysis, the stack traces and the measurements behind this are in
[`docs/asan-leak-check/`](docs/asan-leak-check/README.md).

## Requirements

- `VCPKG_ROOT` in the environment (the machine setup sets it through mise), pointing at a vcpkg checkout with `scripts/buildsystems/vcpkg.cmake`.
- CMake ≥ 3.31, Ninja.
- `gcc-16`, `g++-16`, `clang-p2996` and `clang++-p2996` on PATH under those names, or named through the environment variables `CPP_CORE_CXX` and `CPP_CORE_CC` (for example in the `environment` of a preset in a gitignored `CMakeUserPresets.json`). The triplets pass both through to vcpkg (`VCPKG_ENV_PASSTHROUGH`), so the ports get the same compiler.
- `include-what-you-use` on PATH, for the `p2996-iwyu` preset only.

## Logging

Two logging paths share one quill logger: the **module path** and the **catalog path**.

### The module path

```cpp
import com.rsm.logging;

com::rsm::logging::info("The answer is {}", 42);
```

The module's interface is the whole API: `setup`, `flush`, `set_level`, `current_level`,
`log_raw`, `log`, and the level shortcuts `trace`, `debug`, `info`, `warning`, `error` and
`critical`. The format string is checked at compile time: `format_string<>`'s constructor is
`consteval` and throws (a compile-time error) when the format string is malformed or does not
match the **number** of arguments. (It does not check the *type* of each argument against the
format specification — see the
[features audit](docs/cxx26-features-audit/format-dialect.md).)

The module path reports the call site's file and line, like the catalog path does, and it does it
without a macro. `format_string<>`'s constructor takes the location as defaulted parameters:

```cpp
template <unsigned long N>
consteval format_string(char const (&text)[N], char const *file = __builtin_FILE(),
                         unsigned line = __builtin_LINE(),
                         char const *function = __builtin_FUNCTION())
```

A default argument is evaluated at the call site, so the builtins name the *caller's* file, line
and function, not the module's. The location travels with the format string into `log()`, which
hands it to the implementation, and quill prints it in the `%(short_source_location)` field.
`log_raw()` takes the same defaulted parameters directly.

A macro is the usual way to capture a call site, and it does not work here. A macro defined in
the module's global module fragment does not reach the importing translation units — neither in
clang nor in GCC, both of which drop it — and the module cannot include a header that its
importers include: on both compilers today, the header's declarations and the importer's own
standard headers end up with conflicting attachments (see [Logging](#logging) below). The
default-argument trick needs neither a macro nor a header, and it works the same way on both
compilers.

The alternatives that were measured, the reproductions and the upstream sources are in
[`docs/module-source-location/`](docs/module-source-location/README.md).

The module's interface does not use the standard library. On both compilers today, a standard
header that the module's global module fragment depends on collides with the standard headers of
the translation units that import it:

```
GCC:    error: redefinition of 'constexpr bool std::__is_constant_evaluated()'
Clang:  error: type alias template redefinition with different types ('std::__promote_t')
```

The C++26 text does not require this collision: [module.global.frag]/1 attaches the global module
fragment to the global module, and [std.modules]/4-5 requires implementations to merge `#include`
and `import` without conflicting attachments. Both compilers fail to do that here, so the rule the
project follows is a workaround for a deficiency, not for the standard. The full account is in the
[features audit](docs/cxx26-features-audit/README.md).

So the module formats the messages itself (`modules/logging/format.hpp`, a module-private,
standard-library-free formatter) and reaches its implementation through the
standard-library-free interface in `include/cpp-core/logging/internal.hpp`. The implementation
(`src/logging/quill_logger.cpp`) is a plain translation unit: it is the one place where the
standard library and quill are used.

### The catalog path

```cpp
#include <cpp-core/logging/cib_quill.hpp>

namespace my_module {
CIB_LOG_MODULE("my_module");   // declares cib_log_env_t, so it goes inside a namespace

auto f() {
  CIB_INFO("The answer is: {}", 42);          // 42 is a compile-time argument: folded into the
                                               // format string at compile time
  CIB_INFO("point has {} data members", count); // runtime argument: interpolated by quill's backend
}
} // namespace my_module
```

This path follows the ["binary loggers" section of the cib
documentation](https://github.com/intel/compile-time-init-build/blob/main/docs/logging.adoc#binary-loggers):

- The format string and the compile-time arguments are compile-time values: cib folds the
  compile-time arguments into the format string, and the format string becomes part of the
  message's *type*, so no string data ends up in the payload.
- Each message and each module is identified by an ID from the string catalog, which cib's
  `gen_str_catalog()` tooling assigns at build time. The ID is a function of the message text — it
  is the message's rank among the messages, in text order — so the same message gets the same ID
  under either compiler. It is **not** stable across releases: the build does not feed the previous
  catalog back into the tool, so adding a message renumbers the ones after it. See
  [DEF-6](docs/cxx26-features-audit/open-items.md).
- The payload that goes onto quill's queue is therefore only the metadata of the message (the
  format string, the source location, the tags and the level — all compile-time data, referenced
  rather than copied) plus the runtime values.

`cmake/catalog.cmake` calls `gen_str_catalog()` on the libraries that contain the log calls
(`cpp-core-app` and `cpp-core-test-code`; they are object libraries, so that the tooling can
scan their object files with `nm`). The tooling writes `cpp-core-catalog.cpp` plus the
collateral (`cpp-core-catalog.json`, `cpp-core-catalog.xml`); the generated file is compiled
into the `cpp-core-catalog` library, which the executables link. The catalog of this project
holds three messages (IDs 0 to 2) and one module (`cpp_core`, ID 0):

```json
{
    "messages": [
        {
            "msg": "cib levels map onto quill levels: INFO -> Info, WARN -> Warning",
            "type": "msg",
            "arg_types": [],
            "id": 0,
            "args": [],
            "tags": []
        },
        {
            "msg": "compile-time formatted: the answer is 42",
            "type": "msg",
            "arg_types": [],
            "id": 1,
            "args": [],
            "tags": []
        },
        {
            "msg": "errors are logged too, at quill's Error level",
            "type": "msg",
            "arg_types": [],
            "id": 2,
            "args": [],
            "tags": []
        }
    ],
    "modules": [
        {
            "string": "cpp_core",
            "id": 0
        }
    ],
    "enums": {}
}
```

The IDs are shown in the log line's tag field, next to the cib module:

```
07:01:52.811080209 [51816462] app.cpp:28 LOG_INFO  cpp-core [cpp_core id=1 mod=0] compile-time formatted: the answer is 42
```

The module path has no catalog ID: it formats the message itself, so there is no catalog entry
to refer to.

### What the two paths share

- **Call site fidelity:** the call site's file and line are passed to the logger, so quill
  reports the `CIB_INFO` (or `info`) call site, not the adapter. Both paths report it: the
  catalog path gets it from the `CIB_*` macros, the module path from the defaulted location
  parameters of `format_string<>`'s constructor (see [The module path](#the-module-path)).
- **Levels:** cib's levels follow MIPI Sys-T (0 = most severe); quill's scale runs the other way,
  so they are mapped to keep the relative order — `MAX`→`TraceL3`, `FATAL`→`Critical`,
  `ERROR`→`Error`, `WARN`→`Warning`, `INFO`→`Info`, `USER1`→`Debug`, `USER2`→`TraceL1`,
  `TRACE`→`TraceL2`.
- **Modules:** the cib module is passed to quill as a tag, and shown in the `%(tags)` field of the
  pattern.
- **Threading:** the two paths differ here. The catalog path queues the runtime arguments, and
  quill formats them on its backend thread. The module path formats the message on the calling
  thread — into a fixed 2,048-byte buffer — and then copies it into the queue, so each module-path
  message costs one heap allocation on the calling thread.
- **Format strings:** the two paths **do not** share a dialect. The catalog path formats with
  quill's bundled fmt, which implements the C++26 format-spec grammar and checks it against the
  argument's type; the module path formats with the module's own scanner, which implements the
  *structure* of that grammar but not its validation. So `info("{:>06}", 42)` gives `000042` on the
  module path and `    42` on the catalog path, and a specification that fmt would reject
  (`{:s}` on an `int`) is accepted and ignored by the module path. The fifteen differences are
  listed in the [features audit](docs/cxx26-features-audit/format-dialect.md).
- **ODR:** `logging::config<>` is a variable template: every translation unit that logs with the
  `CIB_*` macros must include `cpp-core/logging/cib_quill.hpp` and link `cpp-core::logging`, or it
  would use cib's null logger.

## Tests

The tests use [ut](https://github.com/stephenberry/ut), the same way glaze does:

```cpp
import com.rsm.logging;

#include "ut/ut.hpp"

using namespace ut;

suite tests = [] {
  "the level can be set and read back"_test = [] {
    com::rsm::logging::set_level(com::rsm::logging::level::warning);
    expect(com::rsm::logging::current_level() == com::rsm::logging::level::warning)
        << "the level was not changed";
  };
};
```

`tests/logging_test.cpp` is an object library (`cpp-core-test-code`), so that the catalog tooling
can scan it for the messages that need a catalog ID; the test executable links the objects. ctest
runs it as `cpp-core-tests`.

The source location of a log call is checked by capturing what the sink writes: the capture
redirects the file descriptor of stdout to a temporary file for the duration of the test, and the
test then looks for `logging_test.cpp:<line>` in it. The line is the line of the log call, so the
check fails if the location is missing or points somewhere else.

A malformed format string is a compile-time error, but inside the `ut` suite the diagnostic is
hard to read: the suite's initializer is evaluated at compile time, and the `consteval`
constructor's throw is reported as `call to immediate function ... is not a constant expression`,
with the notes pointing at the first non-constexpr call in the suite instead of at the format
string. The same call outside the suite names the real cause (`call to consteval function ... is
not a constant expression`).

## Include-what-you-use

The check is integrated into the LLVM/clang preset setup and is off by default, so that the
normal builds are not slowed down:

```sh
cmake --workflow --preset p2996-iwyu    # configure + build + build the iwyu target + test
cmake --build --preset p2996-iwyu       # just the checks
```

`cmake/iwyu.cmake` creates one target per checked translation unit plus the aggregate `iwyu`
target. The checks run with `-Xiwyu --mapping_file=cmake/iwyu_mappings.txt`, and the mapping file
redirects the headers that IWYU would otherwise ask for (the cib and stdx headers, the C standard
library headers) to the headers that this project uses.

The scope is limited by two limitations of the tool, which the configure step prints:

| Source | Checked | Why |
|---|---|---|
| `modules/logging/logging.cppm` | yes | the module interface |
| `src/app.cpp` | yes | the CIB path |
| `src/logging/quill_logger.cpp` | yes | the quill implementation |
| `src/main.cpp` | no | IWYU crashes on a module import |
| `tests/logging_test.cpp` | no | IWYU crashes on a module import |
| `src/reflection_demo.cpp` | no | `<meta>` is not in IWYU's standard library |

IWYU (Homebrew clang 23) crashes when a translation unit imports a module that contains a class
with a user-declared constructor — the logging module has one, the `format_string` class template.
The reflection demo needs `<meta>`, which is not part of Homebrew's libc++ yet.

## Pieces

- **`cmake/toolchains/cpp-core.cmake`** is one toolchain for every compiler. It picks the compiler from `CPP_CORE_COMPILER` by its bare name on PATH and sets the flags for C++26, reflection, libc++, hardening and sanitizers.
- **`cmake/cpp-core-check.cmake`** runs after `project()`. It stops the configure if the compiler found is not the one the preset names (Apple clang for `p2996`, for example, is an error). It then adds the reflection flags to this project's C++ compiles only. They are kept out of `CMAKE_CXX_FLAGS` because GCC 16 rejects `-freflection` below C++26, which would break vcpkg's port builds and CMake's compiler checks in nested projects.
- **`CMakePresets.json` + `cmake/presets/cpp-core.json`**: hidden base presets compose `compiler x config`; the public presets (`gcc16-debug`, `p2996-asan`, ...) inherit from them.
- **`cmake/lsan.supp`** suppresses the leaks that macOS itself causes, for the presets that run the leak check (see [Leak checking](#leak-checking)).
- **vcpkg** runs in manifest mode:
  - `vcpkg.json` pins `builtin-baseline`; add dependencies here (as features, if they are optional).
  - `vcpkg-configuration.json` adds only the overlays. It has no default registry, because one would silently replace the manifest's baseline.
- **`triplets/arm64-osx-<compiler>[-asan|-tsan].cmake`** makes vcpkg build its ports with our toolchain (`VCPKG_CHAINLOAD_TOOLCHAIN_FILE`), so libraries and project share the compiler, standard library and sanitizers.
- **`ports/`** holds overlay ports for libraries vcpkg lacks or that need a patch. They are pinned
  to the latest upstream commit:
  - `intel-cib` (Intel's compile-time-init-build) and its dependencies `intel-cpp-std-extensions`,
    `intel-baremetal-concurrency` and `intel-baremetal-senders-and-receivers`. The cib port also
    installs the string-catalog tooling (`cmake/string_catalog.cmake` and the python script it
    drives), so that a consumer can use `gen_str_catalog()`.
  - `ut` (Stephen Berry's test framework). Header-only: upstream's module variant needs
    `import std`, which puts the `std` module in every test translation unit — and GCC 16 then
    collides with the standard headers the test file includes. CMake's experimental gate is not
    the obstacle: upstream ships the `import std` gate UUIDs itself.

## Without vcpkg

To configure without vcpkg's manifest mode, override the toolchain — and point the search path at
an already-installed vcpkg tree, because that is what vcpkg's own toolchain does
(`vcpkg.cmake:452`). Without the prefix path, `find_package(intel-cib CONFIG REQUIRED)` has nowhere
to look:

```sh
cmake --preset gcc16-release -B build/nv-gcc16-release \
  -DCMAKE_TOOLCHAIN_FILE=$PWD/cmake/toolchains/cpp-core.cmake \
  -DCMAKE_PREFIX_PATH=$PWD/build/p2996-debug/vcpkg_installed/arm64-osx-p2996
```

Use the triplet that matches the compiler: `arm64-osx-p2996` for the `p2996-*` presets and
`arm64-osx-gcc16` for the `gcc16-*` ones.
