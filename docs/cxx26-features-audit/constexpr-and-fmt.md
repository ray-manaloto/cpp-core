# fmt over `std::format`, and making everything `constexpr`

**Date:** 2026-11-11
**Status:** research and plan. **Nothing here is applied to the build** - the build lane is parked,
and every step below that needs a compile is listed as an open question.

This part answers two questions the owner asked:

2. *"We want to use fmtlib over `std::fmt` as it supports constexpr more."*
3. *"Make all our methods constexpr/consteval whenever possible."*

## The short answer

**The owner's premise about fmt is correct, and stronger than expected.** fmt's compile-time API
supports constexpr formatting **including floating point**, and it does **not** need a constexpr
`std::string`. C++26's `std::format` is constexpr (P3391R2), but it explicitly **excludes floating
point** from constant evaluation, and neither standard library on this machine implements it at
all. On this toolchain, today, **fmt is the better constexpr formatter**.

**But fmt cannot enter the logging module's interface**, for exactly the same reason `std::format`
cannot: a textual `#include` inside a module unit produces **global-module** declarations, which
collide with the importing translation unit's own standard headers. So the two asks pull apart:

- **Inside the module**, the only formatter that can be `constexpr` is the project's **own**
  hand-rolled one - so ask #3 means making `format.hpp` fully `constexpr`, which is entirely
  achievable and is the single highest-value change in this document.
- **Outside the module** (the implementation translation unit, the cib path, the tests), fmt is
  available and should be used - most immediately to replace the `snprintf` in `format_double`,
  which also fixes the `{:f}` divergence.

The recommendation is therefore: **use fmt everywhere the standard library is allowed, make the
module's own formatter `constexpr`, and keep `std::format` out of the project entirely.**

## 1. fmt versus `std::format`: the evidence

### 1.1 The comparison

| | `std::format` (C++26) | fmt 12.2.1 (installed) |
|---|---|---|
| constexpr formatting | **yes** - P3391R2 was adopted at Kona in November 2025; the draft's synopsis declares `format`, `format_to`, `vformat_to` and `format_to_n` `constexpr` | **yes** - via `fmt/compile.h`: `FMT_COMPILE`, the `"..."_cf` literal, and `FMT_STATIC_FORMAT` |
| feature-test macro | `__cpp_lib_constexpr_format 202511L` (the draft also defines `__cpp_lib_constexpr_string 202511L`) | none - the API is selected by including `fmt/compile.h` |
| **implemented on this machine?** | **no** - libstdc++ 16 defines no `__cpp_lib_constexpr_format` and declares `std::format` without `constexpr`; libc++ 21 does the same (`__cpp_lib_format` is still `202110L`) and llvm#171292 is open | **yes** - `build/p2996-debug/vcpkg_installed/arm64-osx-p2996/include/fmt/compile.h` is here |
| **floating point at compile time** | **no** - P3391R2 §2.1: only the *integral* overloads of `std::to_chars` are `constexpr`, so "we will not (yet) be able to format floating point ... during constant evaluation time" | **yes** - P3391R2 §2.4: "The {fmt} library has supported compile-time formatting for a while, just through a different API with the format string annotated: as `format_to(out, FMT_COMPILE("x={}"), x)`. **That implementation even supports floating point types at compile time**" |
| needs a constexpr `std::string`? | **yes**, for the `std::string`-returning overload - and neither library has constexpr `std::string` | **no**, for `FMT_STATIC_FORMAT`: it returns `fmt::static_format_result<N>`, which holds a `char data[N]` (`fmt/compile.h:565-578`). The `fmt::format` overload does need it |
| compile-time format-string check | `std::format_string<Args...>` | `fmt::format_string<Args...>`, with `fmt::runtime` to opt out |
| runtime format strings | `std::vformat` | `fmt::vformat`, `fmt::runtime` |
| can it enter the module interface? | **no** - it needs `import std;`, which works on clang-p2996 only, and breaks every importing translation unit on GCC 16 | **no** - see 1.3 |
| dependency status here | none | **transitive only** - quill 13.1.0 bundles its own copy; the standalone fmt 12.2.1 arrives through `intel-cpp-std-extensions` |

**Sources.** fmt's documentation, "Compile-Time Support":
<https://fmt.dev/latest/api/>. fmt 12.0.0 release notes ("Added `constexpr` support to
`fmt::format` ... now works at compile time **provided that `std::string` supports `constexpr`**"):
<https://github.com/fmtlib/fmt/releases/tag/12.0.0>. The tracking issue, fmt#3403, with Victor
Zverovich's comment of 2025-09-07 ("This is supported via the compile-time API as of #4456 and
only requires C++20"):
<https://github.com/fmtlib/fmt/issues/3403>. P3391R2:
<https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2025/p3391r2.html>.

### 1.2 What the installed fmt actually offers

Read from `build/p2996-debug/vcpkg_installed/arm64-osx-p2996/include/fmt/`:

```cpp
// fmt/compile.h:565-578
template <size_t N> class static_format_result {
 private:
  char data[N];

 public:
  template <typename S, typename... T,
            FMT_ENABLE_IF(is_compiled_string<S>::value)>
  explicit FMT_CONSTEXPR static_format_result(const S& fmt, T&&... args) {
    *fmt::format_to(data, fmt, std::forward<T>(args)...) = '\0';
  }

  FMT_CONSTEXPR auto str() const -> fmt::string_view { return {data, N - 1}; }
  FMT_CONSTEXPR auto c_str() const -> const char* { return data; }
};
```

```cpp
// fmt/compile.h:594
#define FMT_STATIC_FORMAT(fmt_str, ...) ...
```

```cpp
// fmt/compile.h:55-60
#if FMT_USE_NONTYPE_TEMPLATE_ARGS
inline namespace literals {
template <detail::fixed_string Str> constexpr auto operator""_cf() {
  return FMT_COMPILE(Str.data);
}
}  // namespace literals
#endif
```

So `static constexpr auto s = FMT_STATIC_FORMAT("{}", 42);` is a **compile-time** constant string,
with no heap allocation and no constexpr `std::string` required. That is exactly the capability
`std::format` cannot provide on this toolchain.

### 1.3 Why fmt cannot enter the module interface

The module's interface is standard-library-free because a textual `#include` inside a module unit
produces declarations **attached to the global module**, and those collide with the importing
translation unit's own standard headers:

```
GCC:    error: redefinition of 'constexpr bool std::__is_constant_evaluated()'
Clang:  error: type alias template redefinition with different types ('std::__promote_t')
```

This applies to the module's **purview** just as much as to its global module fragment: an
`#include` is a textual inclusion, and the declarations in the included header belong to the global
module ([module.unit]/7 attaches only *declarations made in the module unit* to the module; a
header's declarations stay global-module declarations).

`fmt/base.h` includes `<limits.h>`, `<stdio.h>`, `<string.h>`, `<cmath>`, `<cstdint>`, `<cstring>`,
`<iterator>`, `<limits>`, `<memory>`, `<string>`, `<string_view>`, `<type_traits>` and more. So
fmt cannot be included inside `modules/logging/` - **not even in the purview** - on either
compiler.

The only ways in would be `import std;` (clang-p2996 only, and it breaks GCC's importers) or a
fmt module (there is none).

**Consequence:** fmt cannot provide the *compile-time* formatting for the module path. The only
compile-time formatter available to the module is the project's own.

### 1.4 Which fmt - and the two-copies problem

This needs a decision, because quill does **not** use the standalone fmt:

- quill 13.1.0 includes `"quill/bundled/fmt/base.h"` (`quill/core/Codec.h:9`,
  `quill/backend/BackendWorker.h:45`) and there is **no** `QUILL_USE_EXTERNAL_FMT` option in the
  installed headers.
- The bundled copy is fmt **12.2.0** in the namespace **`fmtquill`**; the standalone copy is fmt
  **12.2.1** in the namespace **`fmt`**. They are two different files (166,465 and 163,344 bytes).
- The bundled copy has the same compile-time API, under the `fmtquill` names:
  `fmtquill/bundled/fmt/compile.h:57` has the `"_cf"` literal and `:593` has
  `FMTQUILL_STATIC_FORMAT`.

| | standalone `fmt` 12.2.1 | quill's bundled `fmtquill` 12.2.0 |
|---|---|---|
| namespace | `fmt` | `fmtquill` |
| public API | yes - it is fmt's own API | **no** - it is quill's vendored copy; the namespace is an implementation detail of quill 13.1.0 |
| stable across a quill upgrade | yes | no - a quill release could rename or replace it |
| one copy in the binary? | **no** - two copies if both are used | yes, if it is the only one used |
| a custom `formatter<T>` written for it | works with the project's own calls, **not** with quill's runtime formatter | works with **both** the project's calls and quill's runtime formatter |

**Recommendation: use the standalone `fmt`, and declare it directly in `vcpkg.json`.** The reasons:

1. `fmtquill` is quill's internal namespace. Depending on it couples the project to a detail of a
   pinned dependency; a quill upgrade could break it silently.
2. The project should not depend on a *transitive* dependency. `fmt` is currently in the include
   tree only because `intel-cpp-std-extensions` wants it; adding `"fmt"` to `vcpkg.json` makes it
   explicit and pins it.
3. The **two-copies** cost is real but small: two copies of a header-only library with different
   namespaces. The mitigation is a project rule: **custom formatters are written for `fmt` only**,
   and the cib path (which goes through quill's `fmtquill`) does not need them - it formats
   primitives, and the one project type it formats (`::logging::level`) is decayed to its underlying
   integer by `decay_enum_value` (`cib_quill.hpp:55-61`).

**Open question:** does the vcpkg `quill` port have a feature to use an external fmt? The installed
headers say no; the upstream port might. If it did, the two-copies problem would disappear.

### 1.5 Where fmt should be used

| Place | fmt usable? | What it would replace |
|---|---|---|
| `modules/logging/**` | **no** | - |
| `src/logging/quill_logger.cpp` | yes | `std::snprintf` in `format_double` (`quill_logger.cpp:121-167`) - and this **fixes the `{:f}` divergence**: fmt's default floating-point presentation is the shortest round-trip, and `'f'` gives six digits after the point, exactly as `std::format` does |
| `include/cpp-core/logging/cib_quill.hpp` | yes | the `std::string` concatenation that builds the tags (`cib_quill.hpp:147-148`) becomes `fmt::format`; the rest of that path already goes through quill's fmt |
| `tests/logging_test.cpp` | yes | the hand-rolled stdout capture stays; the assertions can compare against `fmt::format` output instead of literals, which would catch any formatting divergence automatically |
| `src/reflection_demo.cpp` | yes | nothing to replace |

**Note on `format_double`:** it stays **runtime-only**. Its format specification is a runtime
`char` and `int` (the module parses it at runtime), so a compile-time format string is impossible
there - `fmt::format_to_n` would need `fmt::runtime(...)`. That is fine: the point of using fmt
there is the *correct* float rendering, not constexpr-ness.

## 2. Making everything `constexpr` / `consteval`

### 2.1 The rule

A function can be `constexpr` if every path it can take is valid during constant evaluation. A
`constexpr` function may *contain* a call to a non-`constexpr` function - it simply cannot be
constant-evaluated along that path. So the practical rule is:

> Mark a function `constexpr` whenever its own body is constant-evaluable. A branch that cannot be
> constant-evaluated is not a reason to leave the whole function unmarked; it is only a reason that
> *that branch* cannot be used at compile time.

### 2.2 The inventory

`modules/logging/format.hpp` - the module's private formatter. **Every function here can be
`constexpr`.** None of them touches the standard library, the heap, or a runtime facility.

| Function | Line | Now | Verdict | Note |
|---|---|---|---|---|
| `forward` (both overloads) | 126, 130 | - | **constexpr** | `std::forward` is `constexpr`; this is a verbatim copy |
| `message_buffer::append(char)` | 158 | - | **constexpr** | writes into `chars[used++]`; fine in constant evaluation |
| `message_buffer::append(char const *, unsigned long)` | 164 | - | **constexpr** | |
| `message_buffer::append_padded` | 171 | - | **constexpr** | |
| `message_buffer::data()` | 200 | - | **constexpr** | |
| `message_buffer::size()` | 201 | - | **constexpr** | |
| `copy_text` | 300 | - | **constexpr** | |
| `string_length` | 315 | - | **constexpr** | |
| `digit_char` | 323 | - | **constexpr** | the two digit tables are `constexpr` locals; fine |
| `format_integer` | 329 | - | **constexpr** | all arithmetic and local `char` arrays |
| `format_value` | 424 | - | **constexpr**, with one caveat | the floating-point branch calls `format_double`, which is not `constexpr` - so the function is legal as `constexpr`, but a float argument cannot be constant-evaluated |
| `argument_value` | 469 | - | **constexpr** | takes the address of the argument |
| `parse_spec` | 477 | - | **constexpr** | |
| `append_escaped` | 517 | - | **constexpr** | |
| `format_message` | 532 | - | **constexpr**, with one caveat | see 2.3 |
| `scan_format` | 220 | `consteval` | **keep `consteval`** | it exists only to run at compile time |
| `format_matches` | 285 | `consteval` | **keep `consteval`** | same |
| `is_signed_v` | 105 | `constexpr` | keep | |
| the type traits (20-105) | | - | keep | they are compile-time by construction |

`src/logging/quill_logger.cpp`:

| Function | Line | Now | Verdict | Note |
|---|---|---|---|---|
| `to_quill_level(int)` | 37 | - | **constexpr** | a switch over an `int` against `constexpr` constants |
| `from_quill_level(quill::LogLevel)` | 57 | - | **constexpr** | a switch over an enum; `quill::LogLevel` is `enum class LogLevel : uint8_t` (`quill/core/LogLevel.h:31-44`), a literal type |
| `format_double` | 121 | - | **not `constexpr`** | `std::snprintf` is a library call. `std::to_chars` for floating point is **not** `constexpr` in C++26 (P2291R3 made only the integral overloads `constexpr`), so there is no standard-library route either. fmt can format floats at compile time, but only with a compile-time format string, and this function's specification is a runtime `char` |
| `quill_logger`, `start_logger`, `flush_logger`, `set_log_level`, `get_log_level`, `emit` | 83-119 | - | **not `constexpr`** | they start a backend thread, write to a queue, and allocate |

`include/cpp-core/logging/cib_quill.hpp`:

| Function | Line | Now | Verdict | Note |
|---|---|---|---|---|
| `level_of` | 45 | `constexpr` | keep | |
| `decay_enum_value` | 55 | - | **constexpr** | it calls `format_as(t)` (an ADL hook) or `stdx::to_underlying` (which is `constexpr`). As with `format_value`, an ADL function that is not `constexpr` simply makes that path non-constant-evaluable |
| `to_quill_level(::logging::level)` | 68 | `constexpr` | keep | |
| `string_type` | 93 | `consteval` | keep | |
| `module_string_type` | 108 | `consteval` | keep | |
| `quill_config::logger::log` | 130 | - | **not `constexpr`** | it allocates catalog strings and pushes onto quill's queue |

`modules/logging/logging.cppm`:

| Function | Line | Now | Verdict | Note |
|---|---|---|---|---|
| `format_string`'s constructor | 67 | `consteval` | keep | it validates the format string and captures the call site |
| `setup`, `flush`, `set_level`, `current_level`, `log_raw`, `log`, `trace`, `debug`, `info`, `warning`, `error`, `critical` | 86-151 | - | **not `constexpr`** | every one of them has a runtime effect: they start the backend, read or set the level, or hand a message to quill |

`include/cpp-core/logging/internal.hpp`: `start_logger`, `flush_logger`, `set_log_level`,
`get_log_level`, `emit`, `format_double` - **none can be `constexpr`**. They are the runtime
boundary between the module and its implementation, and that is exactly what they are for.

### 2.3 The two caveats, stated precisely

**Caveat 1 - floating point is the one thing that cannot be constant-evaluated.**
`format_value`'s floating-point branch (`format.hpp:448-450`) calls `format_double`, which calls
`std::snprintf`. Marking `format_value` `constexpr` is legal, but a float argument will fail to
constant-evaluate with "call to non-`constexpr` function". Every other argument type - `bool`,
`char`, `char const *`, string literals, every integer type, `std::string`, `std::string_view` and
`self_formatting` types with a `constexpr format_to` - works.

**Caveat 2 - `format_message` needs its arguments to be constants of static storage duration.**
`format_message` builds two local arrays (`format.hpp:539-540`):

```cpp
formatter_fn const formatters[] = {&format_value<remove_cvref_t<Args>>...};
void const *const values[] = {argument_value(args)...};
```

`argument_value` returns the address of the argument (`format.hpp:469-471`). In a constant
expression, the address of an object is a constant expression only if the object has **static
storage duration** and is a constant expression. So:

```cpp
// works: the argument is a constexpr object with static storage
constexpr int answer = 42;
constexpr auto text = format_to_buffer("the answer is {}", answer);

// does not work: the argument is a temporary
constexpr auto text = format_to_buffer("the answer is {}", 42);
```

This is a real constraint on the `static_assert` test pattern, and it is the reason the test helper
has to take its arguments by reference to `constexpr` objects. It is **not** a reason to leave
`format_message` unmarked.

### 2.4 What `constexpr` buys - the concrete payoff

This is the part that makes the change worth more than a keyword:

1. **Compile-time tests.** Every formatting rule - the alignments, the integer bases, the signs, the
   alternate forms, the zero padding, the precisions, the truncations - becomes a `static_assert`
   that the compiler checks. The formatter's behaviour is then verified by the build itself, on
   **both** compilers, with no test binary and no coverage instrumentation. This is a much stronger
   guarantee than a runtime test, and it is exactly what a "100% coverage" target wants: the
   compile-time-only code that the coverage report cannot see (see
   [coverage-gaps.md](coverage-gaps.md), section 1.2) gets verified *instead*.
2. **A compile-time diagnostic for a bad format string.** The `consteval` scanner already rejects a
   malformed format string; with a `constexpr` formatter, the *rendered* result can be checked too.
3. **No runtime cost.** `constexpr` functions that are never constant-evaluated are ordinary
   functions; the only cost is that the compiler may inline more aggressively.

### 2.5 The proposed shape

The change is small and mechanical. In `format.hpp`:

```diff
-template <typename T> [[nodiscard]] auto forward(T &t) noexcept -> T && {
+template <typename T> [[nodiscard]] constexpr auto forward(T &t) noexcept -> T && {
```

and the same for the other fourteen functions in the table above. Nothing else changes: no
signature, no behaviour, no call site.

**A helper for the tests.** The `static_assert` tests need a way to format into a buffer and
compare the result. A `constexpr` helper in `format.hpp` would do it:

```cpp
// Formats a message into a fixed buffer and compares it with the expected text.
template <unsigned long N, typename... Args>
[[nodiscard]] constexpr auto format_equals(char const (&expected)[N], char const *text,
                                           unsigned long length, Args &&...args) -> bool {
  message_buffer buffer;
  format_message(buffer, text, length, std::forward<Args>(args)...);
  return buffer.size() == N - 1U && ...;   // compare the bytes
}
```

with the arguments passed as references to `constexpr` objects (caveat 2). The tests then read:

```cpp
static_assert(format_equals("the answer is 42", "the answer is {}", 16, answer));
```

The test file for this would be a new `tests/format_static_asserts.cpp` - or a block of
`static_assert`s in the existing test file. It needs no test framework and no runtime: it is
verified by the compiler.

### 2.6 What must **not** be made `constexpr`

- `format_double` - `std::snprintf`, and `std::to_chars` for floating point is not `constexpr`.
- every function that starts the backend, touches quill's queue, or allocates.
- `format_string`'s constructor stays `consteval`, not `constexpr`: it exists to run at compile
  time and to *reject* a bad format string by throwing.
- `scan_format` and `format_matches` stay `consteval`.

## 3. The plan, in order

| # | Step | Needs a compile? | Size |
|---|---|---|---|
| 1 | Fix the level-filtering defect and add the test for it | **yes** | 3 lines x 2 + 1 test |
| 2 | Add `"fmt"` to `vcpkg.json` as a direct dependency | yes (a vcpkg reconfigure) | 1 line |
| 3 | Mark the fifteen `format.hpp` functions `constexpr` | **yes** - and the compiler is the test | ~15 keywords |
| 4 | Add the `static_assert` formatter tests | **yes** | a new test file |
| 5 | Replace `std::snprintf` with fmt in `format_double` | **yes** - and the float output changes | ~30 lines |
| 6 | Use `fmt::format` for the cib tag string | yes | 3 lines |
| 7 | Consider moving the formatting to the implementation TU (the big one) | yes | ~400 lines moved, plus the type erasure |

**Steps 3 and 4 are the ones that serve ask #3, and they are cheap.** Step 5 serves ask #2 and
fixes a real divergence. Step 7 is the large one and is the same investigation as
[quill-runtime-formatting.md](quill-runtime-formatting.md) - and it should come last, because
steps 3-6 make the current design *better* whether or not step 7 happens.

**On step 7 and fmt:** moving the formatting to the implementation TU would mean fmt formats at
*runtime* (the format string crosses the boundary as data), so it would **not** use fmt's
compile-time API - and cpp-core's own `consteval` scanner would remain the compile-time check.
That is a real trade: one formatting engine and 400 fewer lines in the importing translation units,
against losing fmt's compile-time checking. It is worth doing only if the type-erasure mechanism
(the custom `quill::Codec`) turns out to work.

## 4. The open questions

These need a compile, and they are the first thing to run when the build lane reopens.

1. **Does `FMT_STATIC_FORMAT` compile on both toolchains?** It needs
   `FMT_USE_NONTYPE_TEMPLATE_ARGS` and a `constexpr` `format_to`. Both are C++20 features, so it
   should - but it has to be checked on GCC 16 and clang-p2996.
2. **Does fmt's compile-time formatting really handle floating point on both toolchains?** P3391R2
   §2.4 says fmt's implementation does; the library is the same on both, but the *compiler* has to
   constant-evaluate it.
3. **Does `FMT_STATIC_FORMAT` need a constexpr `std::string`?** The source says no - it returns a
   `char[N]`-backed `static_format_result` - but the `fmt::format` overload does, and the two
   overloads must not be confused.
4. **Can `format.hpp` be made `constexpr` wholesale, and does the compiler accept it?** The
   functions look constant-evaluable, but `message_buffer` is a 2,048-byte object with a `char`
   array, and the `formatter_fn` / `values` arrays in `format_message` take addresses. The
   compiler is the only authority here.
5. **Does the `static_assert` test pattern work?** Specifically: does `format_message` constant-evaluate
   when its arguments are `constexpr` objects of static storage duration, and fail (cleanly) when
   they are temporaries? The `values[]` array is the risk.
6. **What does fmt produce for the project's float cases?** The switch from `%g` (six significant
   digits) to fmt's shortest round-trip changes the output for `0.1`, `1.0/3.0`, `1e-7`, `1e20` and
   the infinities. And the `{:f}` divergence is fixed as a side effect - `{:f}` would give
   `3.500000`, as `std::format` does.
7. **Does fmt's `format_to_n` behave the same as `snprintf` for the truncation contract?** The
   module truncates at 2,047 bytes silently; fmt's `format_to_n` returns
   `format_to_n_result{count, error_code}` and the error code has to be checked.
8. **Can a custom `fmt::formatter<T>` be written for a project type, and does it interoperate with
   quill's `fmtquill`-based runtime formatter?** If not, the two-copies problem needs a project
   rule about which namespace custom formatters use.
9. **Does the vcpkg `quill` port have an external-fmt feature?** The installed headers say no; the
   upstream port might. If it does, the two-copies problem disappears.
10. **Does `std::source_location::current()` in a default argument on
    `quill_config::logger::log` return the caller's location?** (From
    [macro-reduction.md](macro-reduction.md), section 7.) It may be the reason the CIB macro cannot
    be dropped, because the call goes through the `logging::log<Env>` template.
11. **Does the catalog tooling's `nm` scan still find the same symbols if the cib tag string is
    built with `fmt::format`?** The tags are runtime data, not types, so it should not matter - but
    it has to be measured.
12. **Does `fmt::runtime` exist in fmt 12.2.1's public API** under that name, and is it the right
    way to format a runtime-built specification in `format_double`?

**These twelve are the ones this part raised. The canonical list is
[open-items.md](open-items.md) (part 10), which numbers them `FMT-1` to `FMT-12` and has since
grown a thirteenth - `FMT-13`, the authoritative feature-test macro values on each toolchain,
added by part 11.**

## 5. The recommendation, in one paragraph

**Adopt fmt as the project's formatting library, and declare it in `vcpkg.json`; use it in the
implementation translation unit and the cib path, where the standard library is allowed; keep
`std::format` out of the project entirely, because on this toolchain fmt's compile-time API is
strictly more capable.** **Make the module's own formatter `constexpr` - every function in it can
be - and add `static_assert` tests that verify the formatting rules at compile time, on both
compilers, with no test binary and no coverage instrumentation.** That last change is the one
that turns "the tests do not reach the formatter" from a coverage problem into a compiler-checked
guarantee. The large change - moving the formatting behind the implementation boundary so that fmt
formats at runtime - is worth doing only if the custom `quill::Codec` experiment succeeds, and it
should come after everything else.
