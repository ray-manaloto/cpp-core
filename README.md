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
the standard library, because a module's global module fragment is copied into every translation
unit that imports it (see [Logging](#logging)).

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
- **asan:** `debug` plus AddressSanitizer and UBSan (`-fno-sanitize-recover`, so UB fails the test), with vcpkg's libraries built the same way (`-asan` triplets). Leak checking is off on both compilers, where an ASan binary with leak checking hangs at exit on this Mac.
- **tsan:** `debug` plus ThreadSanitizer, with vcpkg's libraries built with TSan too. TSan cannot share a build with ASan, hence a separate preset.
- **iwyu:** `debug` plus the include-what-you-use checks (see [Include-what-you-use](#include-what-you-use)).

## Requirements

- `VCPKG_ROOT` in the environment (dotfiles sets it through mise), pointing at a vcpkg checkout with `scripts/buildsystems/vcpkg.cmake`.
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
match the arguments.

The module's interface does not use the standard library. A module's global module fragment is
copied into every translation unit that imports it, so a standard header that the interface
depends on ends up next to the standard headers of any translation unit that includes them, and
the two copies collide:

```
GCC:    error: redefinition of 'constexpr bool std::__is_constant_evaluated()'
Clang:  error: type alias template redefinition with different types ('std::__promote_t')
```

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
  `gen_str_catalog()` tooling assigns at build time.
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
    { "msg": "cib levels map onto quill levels: INFO -> Info, WARN -> Warning", "id": 0 },
    { "msg": "compile-time formatted: the answer is 42", "id": 1 },
    { "msg": "errors are logged too, at quill's Error level", "id": 2 }
  ],
  "modules": [ { "string": "cpp_core", "id": 0 } ]
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
  reports the `CIB_INFO` (or `info`) call site, not the adapter. The module path does not report
  a source location: a function of a module cannot know its call site's location without a macro,
  so the field is empty there. The catalog path (the `CIB_*` macros) does report it.
- **Levels:** cib's levels follow MIPI Sys-T (0 = most severe); quill's scale runs the other way,
  so they are mapped to keep the relative order — `MAX`→`TraceL3`, `FATAL`→`Critical`,
  `ERROR`→`Error`, `WARN`→`Warning`, `INFO`→`Info`, `USER1`→`Debug`, `USER2`→`TraceL1`,
  `TRACE`→`TraceL2`.
- **Modules:** the cib module is passed to quill as a tag, and shown in the `%(tags)` field of the
  pattern.
- **Threading:** quill formats on its backend thread, so runtime arguments are queued rather than
  formatted on the calling thread.
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
    `import std`, which CMake only supports behind an experimental gate.

## Without vcpkg

To configure without vcpkg, override the toolchain:

```sh
cmake --preset gcc16-release -B build/nv-gcc16-release -DCMAKE_TOOLCHAIN_FILE=$PWD/cmake/toolchains/cpp-core.cmake
```
