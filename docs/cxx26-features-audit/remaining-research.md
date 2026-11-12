# The four questions that needed no compile

**Date:** 2026-11-12
**Status:** research. **Nothing here is applied to the build.** Four questions were left open when
the audit's other parts were written, and all four can be answered by reading source - a header in
the installed tree, an upstream file, or the project's own files. This part answers them.

| The question | The answer, in one line |
|---|---|
| 1. What does Intel's own `stdx` do for constexpr formatting? | **It uses fmt's compile-time API** - which independently corroborates the fmt decision |
| 2. Is the logger's lifetime and threading sound? | **Yes, with two documented hazards** - and one of them is in the public API |
| 3. Should the project use `ut`'s module variant? | **No** - not because CMake cannot build it, but because it breaks the test TU on GCC 16 |
| 4. What is the state of the upstream blockers? | **The fmt side is resolved**; the standard-library side is not; the clang-tidy side has not moved |

## 1. Intel's `stdx` is fmt-based

The audit's part 6 rejected `stdx::ct_format` as a replacement for the module's formatter, because
`stdx/ct_string.hpp:8-14` includes seven standard headers and `stdx/ct_format.hpp` adds
`<algorithm>`, fmt and Boost.MP11 - so `stdx` cannot enter the module interface. That is still true,
and this part does not reopen it.

But the *reason* it cannot is worth understanding, because it is not "Intel wrote a formatter":

```cpp
// stdx/detail/fmt.hpp:14 - the hosted path
#define STDX_FMT_COMPILE(Fmt) FMT_COMPILE(std::string_view{Fmt})

// stdx/ct_format.hpp:326-331 - the formatting itself, at compile time
template <std::size_t N>
consteval auto perform_format(auto s, auto const &v) -> ct_string<N + 1> {
    ct_string<N + 1> cts{};
    fmt::format_to(cts.begin(), s, v);
    return cts;
}
```

**Intel's compile-time formatter is fmt's compile-time API.** `stdx::ct_format` is a thin layer over
`FMT_COMPILE`, `fmt::formatted_size` and `fmt::format_to` (`ct_format.hpp:336-349`), with a
fixed-capacity `ct_string` as the output. Intel did not write a constexpr formatter; they used fmt's
one.

That is **independent corroboration of the owner's decision**. The two organisations that had to
solve "formatting at compile time" - one for a logging library, one for a freestanding C++ library
- both reached for fmt's compile-time API, and neither wrote a constexpr formatter of their own.

Two more things fall out of the same source.

**The size-first pattern.** Intel computes the output size at compile time
(`constexpr auto sz = fmt::formatted_size(fmtstr, s);`, `ct_format.hpp:341`) and then formats into a
buffer of exactly that size. The module does the opposite: it formats into a fixed 2,048-byte
buffer (`format.hpp:154-206`) and **truncates silently** - `append` drops whatever does not fit
(`format.hpp:158-168`). So the module can produce a log line that ends mid-word with no indication
that it did.

**What a hand-rolled scanner looks like when someone writes one on purpose.** `stdx`'s freestanding
path (`stdx/detail/fmt.hpp`, the `STDX_FREESTANDING` branch - about 140 lines) is a complete
consteval formatter - and it supports exactly two forms:

```cpp
consteval auto parse_fmt_spec(auto fmtstr) -> fmt_spec {
    ...
    if (*i == '}') {
        return {.len = 2, .base = 10};
    } else if (*i++ == ':' and *i++ == 'x' and *i == '}') {
        return {.len = 4, .base = 16};
    }
    return {.well_formed = false};
}
```

and it **validates**:

```cpp
static_assert(spec.well_formed,
  "Freestanding fmt implementation does not support that format specifier");
```

So Intel's hand-rolled scanner is a quarter of the module's size, supports two specifiers instead
of a dozen, and **rejects** what it does not support. The module's scanner is three times the size,
supports more, and **accepts everything**. Part 13 (the format dialect) is the full account of that
difference.

### The stale row in part 6

`intel-libraries.md`'s section 7 listed this as unverified:

> | Project's `format_double` implementation | Only declaration seen in `internal.hpp`; definition in `quill_logger.cpp` (not read). |

It is now read. The declaration is `include/cpp-core/logging/internal.hpp:52-53`; the definition is
`src/logging/quill_logger.cpp:121-167`; it uses `std::snprintf` with `%f`, `%e`, `%E`, `%g` and `%G`;
and it treats `'f'` and the default alike (`quill_logger.cpp:130-137`). Part 6's verdict - that no
Intel facility replaces it - stands, and is now resting on the source rather than on the
declaration.

## 2. The logger's lifetime and threading

Read from `src/logging/quill_logger.cpp`, `include/cpp-core/logging/quill_logger.hpp` and the
installed quill 13.1.0 headers.

### What is sound

| | Evidence |
|---|---|
| **The logger is created exactly once, thread-safely** | `quill_logger()` uses a function-local static with an initializer (`quill_logger.cpp:83-91`); the initialization is done once, and concurrent callers block until it is done ([stmt.dcl]) |
| **The backend is started inside that initializer and stopped at exit** | `quill::Backend::start()` (`quill_logger.cpp:85`) registers `std::atexit([]() { Backend::stop(); })` (`quill/Backend.h:170-175`); quill's own comment is "always call stop on destruction to log everything" (`Backend.h:68-70`). So the project does not have to stop quill, and messages queued before `main` returns are not lost |
| **The level threshold is atomic** | `_log_level` is `std::atomic<LogLevel>` (`quill/core/LoggerBase.h:224`), read and written with relaxed ordering (`LoggerBase.h:135`, `:149`). `set_level()` from any thread is race-free |
| **The project's level round-trip is exact** | `trace → TraceL2 → trace`, `debug → Debug → debug`, `info → Info → info`, `warning → Warning → warning`, `error → Error → error`, `critical → Critical → critical` (`quill_logger.cpp:37-79`) |
| **`set_log_level` cannot be given `Backtrace`** | quill refuses it (`LoggerBase.h:144-147`), and the project never maps to it |

### The two hazards

**Hazard 1 - `flush()` must not be called from a static destructor.** quill's warning is explicit:

> **@warning** Do not call this function from the destructor of a static object. This may lead to
> application crashes if the thread-local ThreadContext is destroyed before the static object
> invoking `flush_log`.
> (`quill/Logger.h:613`)

`flush_log()` blocks the calling thread until the backend has processed the flush
(`Logger.h:604`), and it is the project's **public API**: `com::rsm::logging::flush()`
(`logging.cppm:89`) says nothing about the constraint. The project's own `main()` calls it from
`main`, not from a destructor (`src/main.cpp:15`), so **there is no bug today** - the hazard is for a
*consumer* of the library, who cannot see quill's warning. That is **QUIL-9**.

**Hazard 2 - the two paths format in different places, and only one of them is documented as such.**
Part 13's last section has the detail: the module path formats on the **calling** thread
(`logging.cppm:112-114`) and then copies the message into a `std::string`
(`quill_logger.cpp:118`), so each message costs one heap allocation on the calling thread; the
catalog path queues the arguments and lets the backend format them. The root README's "What the two
paths share → Threading" says only the second.

### One thing that is a policy defect, not a race

**DEF-1 is not a data race.** The threshold is atomic and correct; the module path simply never asks
(`quill_logger.cpp:117-118` calls `log_statement_runtime_metadata` directly, where quill's own
wrappers call `should_log_statement` first - `LogMacros.h:404`, `LogFunctions.h:75`). The backend
then filters against each **sink**'s threshold, whose default is `TraceL3`
(`quill/sinks/Sink.h:279`) - so everything is written. The fix is the three lines DEF-1 describes,
and it needs no synchronisation.

### A minor asymmetry

`from_quill_level` maps quill's `Notice` to the project's `info`, and `TraceL3`/`TraceL1` to
`trace` (`quill_logger.cpp:57-79`). So a level set through **quill's** API - not through
`set_level()` - comes back as the nearest project level. The project's own round-trip is exact, so
this only matters if a consumer mixes the two APIs.

## 3. `ut`'s module variant: reachable, and still not usable

The port's comment says:

> The module variant (modules/ut.ixx) needs `import std`, which CMake only supports behind an
> experimental gate, so this port ships the header-only form.
> (`ports/ut/portfile.cmake:3-5`)

**The first half of that reason is out of date.** Upstream's own `CMakeLists.txt` (vendored at
[`upstream/ut/CMakeLists.txt`](upstream/ut/CMakeLists.txt)) ships a **table of gate UUIDs**, one per
CMake release:

```cmake
set(_ut_import_std_gates
  "3.31=0e5b6991-d74f-4b3d-a41c-cf096e0b2508"
  "4.0=a9e1cf81-9932-4810-974b-6eccaf14e457"
  "4.1=d0edc3af-4c50-42ea-a356-e2862fe7a444"
  "4.2=d0edc3af-4c50-42ea-a356-e2862fe7a444"
  "4.3=451f2fe2-a8a2-47c3-bc32-94786d8fc91b"
  "4.4=f35a9ac6-8463-4d38-8eec-5d6008153e7d"
)
```

and the 4.4 row is **the same UUID** the project's own `import-std.md` uses for CMake 4.4.5. Upstream
also has `option(UT_ENABLE_MODULES "Enable modules with import std" OFF)`, and when it is on,
`set(CMAKE_CXX_MODULE_STD 1)` and `modules/ut.ixx` is added as a module file set. So CMake's gate
is not the obstacle - **upstream has already solved it**, and the vcpkg overlay port could build the
module variant instead of the header-only one.

**But the port's decision is still right, for a sharper reason.** The module variant is:

```cpp
export module ut;
import std;
```

([`upstream/ut/modules/ut.ixx`](upstream/ut/modules/ut.ixx); it uses `std::source_location`,
`std::string_view`, `std::convertible_to`, `std::getenv`, `std::exit`, `std::abort`, `std::clog` and
`std::is_constant_evaluated`.)

So a test translation unit would become:

```cpp
import com.rsm.logging;
import ut;          // which imports std
#include <cstdio>   // tests/logging_test.cpp:13-15
#include <string>
#include <unistd.h>
```

and part 6's matrix already measured what that does on GCC 16:

> **On GCC**, once the `std` module is reachable in a translation unit, any *textual* `#include` of a
> standard or system header in that translation unit collides with the `std.compat` module's
> declarations.
> ([import-std.md](import-std.md), "Why")

`tests/logging_test.cpp` needs those headers - it captures stdout through the C API
(`std::tmpfile`, `::dup`, `::dup2`, `std::fread`, `std::string`, lines 26-69) - so it cannot drop
them. And `import std;` is not a way out either: on GCC 16, `import std;` **plus** `#include
<cstdio>` fails as well (`import-std.md:205`).

**So the answer to MOD-8 is no, and the reason is the project's own constraint rather than CMake's.**
The module variant is reachable - upstream ships it, the gate UUID matches, and the port could build
it - but using it would put the `std` module in the test translation unit, and GCC 16's include
translation then collides with every standard header the test file needs. Fixing that means fixing
GCC's deficiency first (MOD-6), not changing the test framework.

## 4. The upstream watch

Checked on **2026-11-12**.

| Blocker | State | What it means for the project |
|---|---|---|
| [llvm#171292](https://github.com/llvm/llvm-project/issues/171292) - "P3391R2: `constexpr` `std::format`" | **open**; created 2025-12-09, updated 2026-10-09, assigned to `lknknm`, 0 comments | The standard-library side of the fmt decision is unchanged: neither libstdc++ 16 nor libc++ 21 implements P3391R2, so fmt is still the only constexpr formatter available |
| [LWG4531](https://wg21.link/LWG4531) - "Should there be a feature-test macro update for constexpr `std::to_(w)string`?" | **WP** (Brno, 2026-06-13); the reflector selected option B: `__cpp_lib_constexpr_string` 201907L → 202511L | The *macro values* are settled - llvm#171292's own body now cites this issue - so the remaining gap is implementation, not wording |
| [llvm#63939](https://github.com/llvm/llvm-project/issues/63939) - "Clang Tidy too slow and buggy on modules" | **open**; updated 2026-08-25, 3 comments - unchanged since part 3 read it | clang-tidy still checks the non-module translation units only |
| [llvm#62258](https://github.com/llvm/llvm-project/issues/62258) - "`clang-tidy` fails on CXX modules" | **open**; updated 2026-08-25, 8 comments - unchanged | as above |
| [fmt#3403](https://github.com/fmtlib/fmt/issues/3403) - "Enable constexpr support on `format`" | **closed as completed** on 2023-06-17, by `vitaut`; Zverovich's comment of 2025-09-07: "This is supported via the compile-time API as of #4456 and only requires C++20" | **The fmt side of the watch list is resolved.** fmt's constexpr support is not a pending question - it shipped in 2023 and the installed 12.2.1 has it |
| GCC 16's `import std;` mixing deficiency | **no upstream issue is cited**; MOD-6 is still open | The project's constraint is "until GCC fixes it", and MOD-6 is what would tell the project whether it is a header-unit artefact or a merge deficiency |

The one change from what the audit recorded: **fmt#3403 is not a live blocker.** Part 9 cited it for
the *content* of Zverovich's comment, which is right; this part adds the *state*, so that nobody
goes looking for a fmt-side fix that has been in place since 2023.

## What this changes

| The open item | Before | After this part |
|---|---|---|
| MOD-6 (the `ut` module variant) | "re-evaluate now that `import std;` is gated" | **answered: no.** The variant is reachable - upstream ships it, the gate UUID matches - and it breaks the test TU on GCC 16, because the `std` module becomes reachable and the test file needs `<cstdio>`, `<string>` and `<unistd.h>` |
| MOD-8 / the port's comment | "CMake only supports `import std` behind an experimental gate" | the *port* could build the module variant; the reason not to is GCC 16, not CMake. The port's comment should say so |
| QUIL-9 (new) | - | the public `flush()` needs quill's static-destructor caveat, or a safe implementation |
| DEF-1 | "a bug, three lines at each of two call sites" | confirmed, and confirmed to be a **policy** defect rather than a race: the threshold is atomic, and it is the *sink* threshold (default `TraceL3`) that ends up filtering |
| the upstream watch | fmt#3403 listed | fmt#3403 **closed**; LWG4531 **WP**; the other three unchanged |
| part 6's `format_double` row | "not read" | read: `src/logging/quill_logger.cpp:121-167`, `snprintf`-based, `'f'` and the default alike |
| the fmt decision | fmt over `std::format`, on the evidence | **corroborated independently** by Intel's own `stdx`, which is built on `FMT_COMPILE` |

## The method

- **Intel's headers**: **[source]** - read from
  `build/p2996-debug/vcpkg_installed/arm64-osx-p2996/include/stdx/`. The two files this part quotes
  are vendored under [`upstream/stdx/`](upstream/stdx/) so the review can be done offline; they are
  verbatim copies, and the Boost Software License that governs them is beside them.
- **quill's headers**: **[source]** - read from
  `build/p2996-debug/vcpkg_installed/arm64-osx-p2996/include/quill/`.
- **`ut`'s sources**: **[source]** - read from upstream at the port's pinned REF
  `dc65567be78febd265ca36c324e1c504512d4d74`, and vendored under [`upstream/ut/`](upstream/ut/).
  The vendored copies are byte-identical: their git blob hashes
  (`9b68004c4b480ad414a8b1f84d06bdcb2541c51f` for `modules/ut.ixx`, `81a3e3e95f8dc627d942504f997820e3f9a84c23`
  for `CMakeLists.txt`) are the hashes upstream's tree reports for that REF.
- **The upstream issues**: **[measured]** - read from the GitHub API on 2026-11-12; the state and
  the dates are in the table above.
- **The project's own sources**: **[source]** - read in full.

**Nothing was built, configured or run.**
