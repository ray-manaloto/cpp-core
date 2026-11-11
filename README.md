# cpp-core

Modern C++26 project: CMake presets + vcpkg (manifest mode with overlays) + static reflection (P2996).

## Compilers

| Preset prefix | Compiler | Reflection flags |
|---|---|---|
| `gcc16-*` | GCC 16.2 (`g++-16` / `gcc-16`, Homebrew, libstdc++) | `-freflection` |
| `p2996-*` | clang-p2996 (bloomberg/clang-p2996, libc++) | `-freflection -fexpansion-statements -fannotation-attributes` |

## Build

```sh
cmake --workflow --preset gcc16-release    # configure + build + test
cmake --workflow --preset p2996-debug
cmake --list-presets                       # all presets
```

There is one workflow per compiler and configuration; each has configure, build, test and
workflow presets of the same name. Every build directory is `build/<preset>`.

| Compiler | debug | release | asan | tsan |
|---|---|---|---|---|
| GCC 16.2 (`-freflection`) | `gcc16-debug` | `gcc16-release` | `gcc16-asan` | none on macOS (no GCC TSan runtime) |
| clang-p2996 (libc++, reflection) | `p2996-debug` | `p2996-release` | `p2996-asan` | `p2996-tsan` |

- **release:** `Release`, standard library hardening off.
- **debug:** `Debug`, libc++ hardening set to `debug`. On GCC this is `_GLIBCXX_ASSERTIONS`.
- **asan:** `debug` plus AddressSanitizer and UBSan (`-fno-sanitize-recover`, so UB fails the test), with vcpkg's libraries built the same way (`-asan` triplets). Leak checking is off on GCC 16, where an ASan binary with leak checking hangs at exit on this Mac.
- **tsan:** `debug` plus ThreadSanitizer, with vcpkg's libraries built with TSan too. TSan cannot share a build with ASan, hence a separate preset.

`src/main.cpp` is a reflection smoke test, run by ctest as `cpp-core-smoke`: it proves the compiler, the C++26 standard and the reflection flags reach the build on both compilers.

## Requirements

- `VCPKG_ROOT` in the environment (dotfiles sets it through mise), pointing at a vcpkg checkout with `scripts/buildsystems/vcpkg.cmake`.
- CMake ≥ 3.31, Ninja.
- `gcc-16`, `g++-16`, `clang-p2996` and `clang++-p2996` on PATH under those names, or named through the environment variables `CPP_CORE_CXX` and `CPP_CORE_CC` (for example in the `environment` of a preset in a gitignored `CMakeUserPresets.json`). The triplets pass both through to vcpkg (`VCPKG_ENV_PASSTHROUGH`), so the ports get the same compiler.

## Logging

Logging uses [Intel's compile-time-init-build (cib)](https://github.com/intel/compile-time-init-build) logging interface with [quill](https://github.com/odygrd/quill) as the logger.

cib splits logging in two: the interface (`<log/log.hpp>`, the `CIB_*` macros) and an implementation the application selects. The implementation here is `include/cpp-core/logging/cib_quill.hpp`, which specializes `logging::config<>` with a logger that forwards to quill:

```cpp
#include <cpp-core/logging/cib_quill.hpp>

namespace my_module {
CIB_LOG_MODULE("my_module");   // declares cib_log_env_t, so it goes inside a namespace

auto f() {
  CIB_INFO("The answer is: {}", 42);   // 42 is a compile-time argument: folded into the format
                                       // string at compile time
  CIB_INFO("point has {} data members", count);   // runtime argument: formatted by quill's backend
}
} // namespace my_module
```

- **Call site fidelity:** cib passes `__FILE__`/`__LINE__` to the logger, so quill reports the `CIB_INFO` call site, not the adapter.
- **Levels:** cib's levels follow MIPI Sys-T (0 = most severe); quill's scale runs the other way, so they are mapped to keep the relative order — `MAX`→`TraceL3`, `FATAL`→`Critical`, `ERROR`→`Error`, `WARN`→`Warning`, `INFO`→`Info`, `USER1`→`Debug`, `USER2`→`TraceL1`, `TRACE`→`TraceL2`.
- **Modules:** the cib module is passed to quill as a tag, and shown in the `%(tags)` field of the pattern.
- **Threading:** quill formats on its backend thread, so runtime arguments are queued rather than formatted on the calling thread.
- **ODR:** `logging::config<>` is a variable template: every translation unit that logs must include `cpp-core/logging/cib_quill.hpp` and link `cpp-core::logging`, or it would use cib's null logger.
- `cpp_core::logging::setup()` starts quill's backend (done automatically on the first log call), and `cpp_core::logging::flush()` waits for the queued messages to be written.

The cib library is not in the vcpkg registry, so `ports/intel-cib` and its dependencies (`ports/intel-cpp-std-extensions`, `ports/intel-baremetal-concurrency`, `ports/intel-baremetal-senders-and-receivers`) are overlay ports, pinned by commit.

## Pieces

- **`cmake/toolchains/cpp-core.cmake`** is one toolchain for every compiler. It picks the compiler from `CPP_CORE_COMPILER` by its bare name on PATH and sets the flags for C++26, reflection, libc++, hardening and sanitizers.
- **`cmake/cpp-core-check.cmake`** runs after `project()`. It stops the configure if the compiler found is not the one the preset names (Apple clang for `p2996`, for example, is an error). It then adds the reflection flags to this project's C++ compiles only. They are kept out of `CMAKE_CXX_FLAGS` because GCC 16 rejects `-freflection` below C++26, which would break vcpkg's port builds and CMake's compiler checks in nested projects.
- **`CMakePresets.json` + `cmake/presets/cpp-core.json`**: hidden base presets compose `compiler x config`; the public presets (`gcc16-debug`, `p2996-asan`, ...) inherit from them.
- **vcpkg** runs in manifest mode:
  - `vcpkg.json` pins `builtin-baseline`; add dependencies here (as features, if they are optional).
  - `vcpkg-configuration.json` adds only the overlays. It has no default registry, because one would silently replace the manifest's baseline.
- **`triplets/arm64-osx-<compiler>[-asan|-tsan].cmake`** makes vcpkg build its ports with our toolchain (`VCPKG_CHAINLOAD_TOOLCHAIN_FILE`), so libraries and project share the compiler, standard library and sanitizers.
- **`ports/`** holds overlay ports for libraries vcpkg lacks or that need a patch (currently the cib family; see [Logging](#logging)).

## Without vcpkg

To configure without vcpkg, override the toolchain:

```sh
cmake --preset gcc16-release -B build/nv-gcc16-release -DCMAKE_TOOLCHAIN_FILE=$PWD/cmake/toolchains/cpp-core.cmake
```
