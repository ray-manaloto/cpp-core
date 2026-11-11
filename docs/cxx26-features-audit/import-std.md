# `import std;` and the standard-library-free module rule

**Date:** 2026-11-11
**Status:** research. Nothing here is applied to the build.

## The question

`modules/logging/logging.cppm` deliberately avoids the standard library. The reason is written at
the top of the file:

> The module's interface deliberately avoids the standard library. A module's global module
> fragment is copied into every translation unit that imports it, so a standard header that the
> module's interface depends on would end up next to the standard headers of any translation unit
> that includes them, and the two copies collide:
>
> ```
> GCC:    error: redefinition of 'constexpr bool std::__is_constant_evaluated()'
> Clang:  error: type alias template redefinition with different types ('std::__promote_t')
> ```

C++26 has a standard library *module*. Does `import std;` remove the constraint, or does it only
move it?

## The answer

**`import std;` works on both toolchains today - but it removes the constraint only on
clang-p2996.** On GCC 16 it moves the constraint from the module to every translation unit that
imports the module.

## What was verified

The following was measured on this machine (scratch projects under the approved temporary
directory, CMake 4.4.5 + Ninja 1.13.2, `g++-16` = Homebrew GCC 16.2.0 with libstdc++
`__GLIBCXX__=20260807`, `clang++-p2996` = bloomberg/clang-p2996 21.0.0git with libc++
`_LIBCPP_VERSION=210000`). No file in the repository was written.

### The gate

`import std;` needs CMake's experimental support, which is off by default:

```cmake
# before project()
set(CMAKE_EXPERIMENTAL_CXX_IMPORT_STD "f35a9ac6-8463-4d38-8eec-5d6008153e7d")
# per target, or globally
set(CMAKE_CXX_MODULE_STD ON)
```

The UUID is version-specific and has to be looked up for the CMake in use:

| CMake | UUID |
|---|---|
| 4.4.0 and later | `f35a9ac6-8463-4d38-8eec-5d6008153e7d` |
| 4.3.x | `451f2fe2-...` |
| 3.30 - 3.31.7 | `0e5b6991-...` |

Other requirements: Ninja 1.11 or later (header units are not supported by CMake), and
`-fmodules` for GCC (not implied by `-std=c++26`; GCC 16 still defaults to `gnu++20`).

Sources: [CMake `CXX_MODULE_STD`](https://cmake.org/cmake/help/latest/prop_tgt/CXX_MODULE_STD.html),
[`CMAKE_CXX_MODULE_STD`](https://cmake.org/cmake/help/latest/variable/CMAKE_CXX_MODULE_STD.html),
[the cmake-cxxmodules manual's "import std Support" section](https://cmake.org/cmake/help/latest/manual/cmake-cxxmodules.7.html#import-std-support),
[the CMake experimental-gate UUID history](https://discourse.cmake.org/t/cmake-experimental-cxx-import-std-value-history-and-state/15712),
[the GCC 16 changes page](https://gcc.gnu.org/gcc-16/changes.html),
[the GCC 16 C++ modules manual](https://gcc.gnu.org/onlinedocs/gcc-16.2.0/gcc/C_002b_002b-Modules.html).

### The matrix that matters

The same module was built three ways and imported four ways:

| The importing translation unit | GCC 16.2 | clang-p2996 + libc++ 21 |
|---|---|---|
| `import mylib; import std;` (no textual headers) | works | works |
| `import mylib;` + `#include <cstdio>` | **fails** - `conflicting imported declaration 'typedef struct __sFILE FILE'` | works |
| `import mylib; import std;` + `#include <cstdio>` | **fails** - `redefinition of 'void std::__terminate()'` | works |
| the module exports no std types, importer + `#include <cstdio>` | **fails** | works |

### Why

Two different mechanisms are at work.

**On clang**, in C++23+ semantics a module's global module fragment is *attached to the global
module* rather than textually re-included into each importer. Clang therefore merges the
importer's `#include <cstdio>` with the `std` module's own copy of the header declarations
without complaint.

**On GCC**, once the `std` module is reachable in a translation unit, any *textual* `#include` of a
standard or system header in that translation unit collides with the `std.compat` module's
declarations. GCC's "include translation" - which rewrites an `#include` of an importable standard
library header into an `import` of the `bits/stdc++.h` **header unit** - only fires when that
header unit exists. CMake's GCC path builds the `std` **module**, not the header unit, so the
translation does not fire.

The practical consequence for cpp-core is precise:

- **On clang-p2996 the module may `import std;` in its purview, with an empty global module
  fragment, and every importing translation unit keeps its own `#include`s.** That unblocks
  `std::source_location`, `std::format_string`, `std::expected` and `std::optional` inside
  `logging.cppm`, and the hand-rolled `__builtin_FILE` / `__builtin_LINE` / `__builtin_FUNCTION`
  triple can be replaced by `std::source_location`.
- **On GCC 16 the same import compiles, but every translation unit that imports the logging module
  would have to stop including standard headers.** In cpp-core that is `src/app.cpp`,
  `src/main.cpp`, `src/reflection_demo.cpp` and `tests/logging_test.cpp` - and those files include
  quill's and cib's headers, `<unistd.h>` and so on. It is a project-wide migration, not a change
  to one file.

### The manual route is not an option

Driving `import std;` by hand rather than through CMake does not work:

- **clang + libc++'s modulemap path fails**: libc++'s `<complex>` uses the `INFINITY` and `NAN`
  macros, which are not visible in a module context
  (`error: use of undeclared identifier 'INFINITY'`), and after working around that clang reports
  `error: import of module 'std' imported non C++20 importable modules` because the modulemap's
  `std` transitively imports the header modules `std_core` and `std_config`, which have non-empty
  global module fragments. The root cause of that error is not understood. CMake's `std.cppm` path
  avoids it.
- **GCC's manual path**: `g++-16 --compile-std-module -fmodules` produces `gcm.cache/std.gcm`, but
  GCC resolves the CMI path relative to the current working directory, so `-I` and `-isystem` do
  not help, and `-fmodule-mapper=std=file=...` is rejected ("failed opening mapper"). CMake
  generates a mapper file in GCC's format, which is why the CMake route works.

## The three options

### (a) Keep the module standard-library-free - the status quo

The 607-line `modules/logging/format.hpp` stays, and `std::source_location` stays out of reach.

- **Pro:** one code path, both compilers, no experimental CMake gate, no dependency on the
  standard library module's maturity, no risk to the importers.
- **Con:** the project keeps re-implementing `std::format`, `std::to_chars` and the type traits,
  and the format specification it implements is a subset of the standard's with at least one
  divergence (`{:f}`).

### (b) `import std;` in the module's purview on clang-p2996 only

- **Pro:** the module can use the standard library on one of the two compilers; the importers do
  not change at all; `std::source_location` replaces the `__builtin_*` triple.
- **Con:** **two divergent code paths.** The formatter would have to exist twice - once as a
  standard-library-free header for GCC and once using `std::format` for clang - unless the
  implementation is factored so that the *interface* stays standard-library-free and only the
  *implementation* differs. That factoring is possible: `modules/logging/format.hpp` is already a
  module-private implementation detail, and `include/cpp-core/logging/internal.hpp` is already the
  standard-library-free boundary between the module and `src/logging/quill_logger.cpp`. Moving the
  formatting to the implementation side of that boundary would put `std::format` on the plain
  translation unit - but then the arguments have to cross the boundary, which is a type-erasure
  problem (see part 3 of the audit).
- **Con:** it depends on an experimental CMake gate with a version-specific UUID.

### (c) `import std;` everywhere, and migrate every importer

- **Pro:** one code path; the module can use the whole standard library; `std::format` can be used
  directly.
- **Con:** the migration is large and touches the third-party headers. The importing translation
  units would have to use `import std;` *and* keep including quill's, cib's and POSIX headers; the
  tests use `<unistd.h>`, which is not a standard header and is not in the `std` module at all, so
  the tests would have to mix `import std;` with a textual POSIX include. The catalog tooling
  (`gen_str_catalog`) scans the object files for undefined symbols, and the module's object layout
  would change.
- **Con:** it turns on an experimental CMake feature for the whole project.

## The recommendation

**Keep (a) for now, and design the code so that (b) is cheap later.**

The concrete way to do that: keep the module's *interface* standard-library-free (it is what the
importers see, and it is what makes the two compilers work), and put the standard-library-dependent
work behind `include/cpp-core/logging/internal.hpp`, which already exists for exactly this purpose.
Then `std::format` becomes available on both compilers without `import std;` at all - the
implementation is a plain translation unit (`src/logging/quill_logger.cpp`) and may use the standard
library freely today.

What that costs is the type erasure: the arguments of a log call would have to cross the
`emit()` boundary in a form that `std::format` can consume at the other end. That is the
subject of a separate investigation, and it is the same investigation that decides whether
`format.hpp` can shrink.

**Do not adopt (c).** It is a project-wide migration for a benefit that (b) plus the existing
`internal.hpp` boundary can deliver in a much smaller change.

## Open questions

1. How large is the GCC migration in option (c), exactly? Which of the importers' headers would
   have to become `import std;`, and does the POSIX include in the tests survive the mix?
2. Can the type-erasure boundary of option (b) be made to work with a small, fixed-size
   representation - a function pointer table, a variant of primitives - and how much code would
   that be?
3. What does the C++26 standard say about a translation unit that imports the `std` module and
   includes a **non**-standard header such as `<unistd.h>`? Is that ill-formed, or is only the
   mixing of the `std` module with the *standard* headers prohibited?
4. Does the `std` module's own global module fragment (libc++'s generated `std.cppm` includes every
   standard header) re-introduce the original collision on the importing side under GCC? The
   measurement says no - the collision on GCC comes from `std.compat` versus the SDK headers - but
   the standard's wording should be checked against the measurement.
