# What the standard library actually gives, on both toolchains

**Date:** 2026-11-11
**Status:** research. **Nothing here is applied to the build.** This part is a **verified sweep** of
the C++26 library facilities against the two standard libraries the project builds against, read
straight out of the installed headers. It sharpens one row of the audit's table and settles several
questions the earlier parts had to leave open.

## The two trees

| | Path | Version |
|---|---|---|
| libstdc++ | `/opt/homebrew/Cellar/gcc/16.2.0/include/c++/16` | GCC 16.2.0 |
| libc++ | `~/.local/share/p2996/562409c7942690d59ea470762515f88f24b16e23-160a5a16bc16/include/c++/v1` | libc++ 21.0.0 (`_LIBCPP_VERSION 210000`) |

These are the trees the project's own compilers use: `g++-16` resolves to
`/opt/homebrew/Cellar/gcc/16.2.0/bin/g++-16`, and `clang++-p2996` to
`~/.local/share/p2996/562409c7942690d59ea470762515f88f24b16e23-160a5a16bc16/bin/clang-21`.

## The method, and the two traps in it

The sweep reads the feature-test macros out of `<version>` and `<bits/version.h>` / `<__config>`.
Two things about that go wrong if you do it carelessly, and both went wrong the first time.

**Trap 1 - libc++'s `<version>` opens with a synopsis that is not a definition.** The file begins
with a `/* version synopsis */` block (lines 13-279) that tabulates every macro the library *knows
about*, including the ones it has **not** implemented - whose real `#define` further down is
commented out (`version:570` is `// # define __cpp_lib_function_ref 202306L`). Grepping the file
without stripping C comments reports libc++ as having `<inplace_vector>`. **It does not**: the
header is absent, and the synopsis entry is commented out at `version:573`.

**Trap 2 - both libraries define their macros inside per-standard-version branches.** libstdc++
guards them on `(__cplusplus >= N)` (`bits/version.h:1544-1561` for
`__cpp_lib_constexpr_string`, `:1022-1040` for `__cpp_lib_optional`); libc++ guards them on
`_LIBCPP_STD_VER` (`version:447-448`, `:602-603`). So a header's macro is **not one number** - it
is one number per branch. Taking "the last `#define` in the file" picks the *oldest* branch, which
is how a first pass reported libstdc++'s `__cpp_lib_optional` as `201606L` (the C++17 value) when
the C++23+ branch declares `202110L` and the C++27 branch `202506L`.

**So the sweep reports declaration, not a value.** The values are listed as the *set* each macro is
declared with, because which one applies depends on the standard version and on the build's
configuration. The authoritative per-compiler answer needs the preprocessor, which the build lane
has parked - so that is an open item (FMT-13 in
[open-items.md](open-items.md)), not an assertion here.

**What is unambiguous, and what the decisions need, is whether a facility is declared at all and
whether its header exists.** That is what the table gives.

## The sweep

| Facility | libstdc++ 16 | libc++ 21 |
|---|---|---|
| `std::inplace_vector` | declared 202603L | **absent** |
| `std::function_ref` | declared 202603L | header only, no macro |
| `std::move_only_function` | declared 202110L | header only, no macro |
| `std::generator` | declared 202207L | **absent** |
| `std::text_encoding` | declared 202306L | **absent** |
| `std::stacktrace` | declared 202011L | **absent** |
| `std::simd` | header only, no macro | **absent** |
| `std::linalg` | **absent** | **absent** |
| `std::mdspan` | declared 202207L / 202406L | declared 202207L / 202406L |
| `std::flat_map` | declared 202511L | declared 202207L |
| `std::flat_set` | declared 202511L | declared 202207L |
| `std::print` / `println` | declared 202406L | declared 202207L |
| `std::format` | declared 202304L / 202603L | declared 202110L |
| **constexpr `std::format`** | **header only, no macro** | **header only, no macro** |
| constexpr `std::string` | declared 201611L / 201811L / 201907L | declared 201907L |
| constexpr `std::vector` | declared 201907L | declared 201907L |
| `std::expected` | declared 202211L | declared 202211L |
| `std::to_underlying` | declared 202102L | declared 202102L |
| `std::byteswap` | declared 202110L | declared 202110L |
| `std::unreachable` | declared 202202L | declared 202202L |
| `std::source_location` | declared 201907L | declared 201907L |
| `std::ranges::to` | declared 202202L | declared 202202L |
| `std::ranges::zip` | declared 202110L | header only, no macro |
| `std::containers` (the free functions) | **absent** | **absent** |
| `std::execution` (P2300) | header only - **see below** | header only, no macro |
| `std::from_chars` (floating point) | **header only, no macro** | **header only, no macro** |
| `std::to_chars` (floating point) | declared 201611L / 202306L | header only - **see below** |
| `std::optional` monadic | declared 201606L / 202106L / 202110L / 202506L | declared 201606L / 202106L / 202110L |
| `std::hardware_interference_size` | declared 201703L | declared 201703L |
| `std::atomic_ref` | declared 201806L / 202603L | declared 201806L |
| `std::string::contains` | declared 202011L | declared 202011L |
| `std::string::resize_and_overwrite` | declared 202110L | declared 202110L |
| `std::span` | declared 202002L / 202311L | declared 202002L |
| `std::numbers` | declared 201907L | declared 201907L |
| `std::bit_cast` | declared 201806L | declared 201806L |
| `std::is_constant_evaluated` | declared 201811L | declared 201811L |

### The buckets

| | Count | Facilities |
|---|---|---|
| **declared in both** | 22 | `mdspan`, `flat_map`, `flat_set`, `print`/`println`, `format`, constexpr `string`, constexpr `vector`, `expected`, `to_underlying`, `byteswap`, `unreachable`, `source_location`, `ranges::to`, optional-monadic, `hardware_interference_size`, `atomic_ref`, `string::contains`, `string::resize_and_overwrite`, `span`, `numbers`, `bit_cast`, `is_constant_evaluated` |
| **libstdc++ only** | 9 | `inplace_vector`, `function_ref`, `move_only_function`, `generator`, `text_encoding`, `stacktrace`, `ranges::zip`, `execution`, `to_chars` (floating point) |
| **libc++ only** | 0 | - |
| **in neither** | 5 | `simd`, `linalg`, constexpr `format`, `containers`, `from_chars` (floating point) |

**libc++ 21 is behind libstdc++ 16 on every one of these that matters, and ahead on none.** That is
the shape of the constraint the whole project has been working around: two compilers must keep
working, so a facility has to be in **both**, and the nine libstdc++-only ones are therefore off
the table for shared code.

## Three cells the macro does not tell the whole story

### `std::to_chars` for floating point - in **both**, but only one bumped its macro

libstdc++ 16 declares `__cpp_lib_to_chars` with 202306L in its C++26 branch. libc++ 21 **has the
floating-point overloads** - `charconv:39-50` declares `to_chars` for `float`, `double` and
`long double` - but left its active `__cpp_lib_to_chars` at the C++17 value (`version:372`; the
202306L entry at `version:602-603` is commented out).

So the *capability* is in both, and the *macro* under-reports libc++. **The project's `format_double`
could use `std::to_chars` for floats on both compilers** - it just cannot rely on the feature-test
macro to tell it so.

This does **not** change the audit's conclusion about `constexpr`: `std::to_chars` for floating
point is **not** `constexpr` in C++26. P2291R3 made only the *integral* overloads `constexpr`, so
even a `to_chars`-based float formatter would be runtime-only, exactly like `snprintf` is now.

### `std::execution` - the macro is C++17's, not C++26's

libstdc++ 16 declares `__cpp_lib_execution 201902L`. That is **P0443**, the C++17 parallel
algorithms - *not* P2300, the C++26 senders/receivers. libstdc++ 16's `<execution>` contains no
`std::execution::` namespace and no senders at all. libc++ 21 has the header but declares no macro.

**C++26 `std::execution` is in neither library.** The audit's table did not say otherwise, but the
label "libstdc++ only" would have been wrong, so it is recorded here.

### `std::simd` - a header with nothing behind it

libstdc++ 16 ships `<simd>` with **no `std::simd` class in it** (no `class simd` / `struct simd`).
libc++ 21 has no `<simd>` at all. `std::simd` is in neither, in any usable form.

## The two corrections to the audit's table

### Correction 1 - "constexpr `std::string` / `constexpr std::vector`: no"

The audit's table (part 1) says:

> | `constexpr std::string` / `constexpr std::vector` | **no** | P2278 is not implemented |

**The verdict stands; the reason was imprecise.** Both libraries *do* declare
`__cpp_lib_constexpr_string` and `__cpp_lib_constexpr_vector` - libc++ 21 at 201907L for both,
libstdc++ 16 at 201611L/201811L/201907L depending on the standard branch. But that macro denotes
the **partial** constexpr support: a `std::string` you can *construct* at compile time, and a
`std::vector` you can construct and clear - **not** constexpr mutation and **not** constexpr
allocation.

libc++ 21 puts `_LIBCPP_CONSTEXPR_SINCE_CXX20` on the `basic_string(const _CharT*, size_type)`
constructor (`string:1068`), so `constexpr std::string s = "abc";` compiles there.

**Neither library can build a `std::string` by formatting at compile time.** That is what the
project would need, and it is why the audit's conclusion - wait for the libraries - does not change.
The row should read: *partial constexpr only; no constexpr mutation, no constexpr allocation, and
no constexpr `std::format` in either library.*

### Correction 2 - `std::from_chars` for floating point is in neither

The audit did not mention `std::from_chars` at all. It is worth mentioning because it closes off an
option: **neither library declares `__cpp_lib_from_chars`**, so a `from_chars`-based float *parser*
is not available on either compiler. `to_chars` is (see above), `from_chars` for floats is not.

For a logging library this matters only in the other direction - it confirms that the project's
hand-rolled `format_double` has no standard-library escape route, in either direction.

## What this changes for the project's own code

Nothing in the audit's table of hand-rolled things changes its verdict. But three rows gain
precision:

| Audit row | Before | After this sweep |
|---|---|---|
| 4 - `message_buffer` -> `std::inplace_vector` | **defer**: "libc++ 21 has no `<inplace_vector>`" | **confirmed**: libc++ 21 has no `<inplace_vector>` at all (not merely a missing macro), and Homebrew LLVM 23's libc++ has none either. The deferral is correct, and it is a *header absence*, not a version bump waiting to happen |
| 6 - `format_integer` -> `std::to_chars` | "replace if the module may use the standard library" | unchanged - and note the integral overloads **are** `constexpr` (P2291R3), so this one is a `constexpr`-usable replacement where the float one is not |
| 10 - `format_double` -> fmt | "replace, and fix a divergence" | unchanged, and now with the reason spelled out: `std::to_chars` for floats is **available** on both compilers but **not `constexpr`**, and `std::from_chars` for floats is **not available** at all. fmt's compile-time API is the only `constexpr` float formatter in existence |

And the two audit conclusions that depended on the libraries not being ready are now **verified
rather than inferred**:

- **constexpr `std::format` is in neither library** - no `__cpp_lib_constexpr_format` anywhere in
  either tree. llvm#171292 is still open. Part 9's fmt-over-`std::format` recommendation rests on
  this and on fmt's own compile-time API, and it holds.
- **`std::inplace_vector` is libstdc++-only**, so the fixed-capacity message buffer cannot become
  one without dropping a compiler.

## What this does not settle

- **The authoritative macro values.** The table gives declaration; the value that applies to a
  C++26 build on each compiler needs the preprocessor. That is `FMT-13` in
  [open-items.md](open-items.md) - it needs the build lane reopened, and it is a one-line
  `#include <version>` + a static assert.
- **Whether the facilities that *are* declared actually work at C++26.** Declaration is a promise
  by the library; using it is a compile. `std::format` is declared by libc++ 21 with the C++20
  value and does not work at C++26 in the way the standard describes - the same gap, in a smaller
  way, could exist elsewhere.
- **Anything about the module boundary.** Part 4 still governs: a facility in both libraries is
  still unusable *inside the module's interface*, because the module may not name the standard
  library at all. This part is about what the **implementation** translation units and the **cib
  path** may use.

## The method

Every claim in this part is **[source]**: read from an installed header, with file:line. The sweep
itself is reproducible: it reads `version` and `bits/version.h` from the libstdc++ tree, `version`
and `__config` from the libc++ tree, strips C comments, and takes the uncommented `#define`s.
