# Macros: what they do, and whether a template can do it

**Date:** 2026-11-11
**Status:** research. Nothing here is applied to the build.

## The question

Can the macros in cpp-core be reduced or eliminated in favour of C++26 features, static reflection
and template metaprogramming?

## The answer

**The macros are sugar, not a language necessity - but the sugar is worth its price here.**

cpp-core defines **no macros of its own** (verified: `#define` appears nowhere in `src/`,
`include/`, `modules/`, `tests/`, `cmake/` or `CMakeLists.txt`). The entire macro surface of the
project is **four invocations** of Intel's `CIB_*` macros, all in one file
(`src/app.cpp:21,28,29,30`):

```cpp
CIB_LOG_MODULE("cpp_core");
CIB_INFO("compile-time formatted: the answer is {}", answer);
CIB_WARN("cib levels map onto quill levels: {}", "INFO -> Info, WARN -> Warning");
CIB_ERROR("errors are logged too, at quill's Error level");
```

Each of them does something a plain function call cannot do *as written* - but each has a
macro-free equivalent that costs verbosity instead. The mechanism underneath is **already
macro-free**: `logging::log<Env>` is a function template, `stdx::ct_format<Fmt>` is a variable
template, and the compile-time environment is a type. The macros are a front end that lets the
caller write a format string as an ordinary argument and a level as an ordinary word.

The honest summary:

- **The CIB macros stay**, because the project gets the string catalog and the compile-time
  format folding from them, and the macro-free spelling of the same calls is materially noisier
  at every call site.
- **The one thing worth doing macro-free is the call-site capture in the cib path**, because
  `std::source_location` is available there today (that path is *not* standard-library-free).
- **The `stdx` constexpr facilities cannot replace the module's hand-rolled scanner**, because
  they pull in the standard library, and the module interface must not have it. This is the
  decisive fact, and it is in section 4.
- **Reflection cannot help at all here**, for the same reason it cannot help the formatter: a
  `std::meta` range cannot be walked in a constant expression today (see
  [reflection.md](reflection.md)).

## 1. The expansion chain, from `CIB_INFO` down to quill

Every definition below is quoted from the installed Intel headers at
`build/p2996-debug/vcpkg_installed/arm64-osx-p2996/include/`.

### Step 1 - the macro picks the level (`log/log.hpp:71-78`)

```cpp
#define CIB_TRACE(...)  CIB_LOG_WITH_LEVEL(logging::level::TRACE __VA_OPT__(, ) __VA_ARGS__)
#define CIB_INFO(...)   CIB_LOG_WITH_LEVEL(logging::level::INFO  __VA_OPT__(, ) __VA_ARGS__)
#define CIB_WARN(...)   CIB_LOG_WITH_LEVEL(logging::level::WARN  __VA_OPT__(, ) __VA_ARGS__)
#define CIB_ERROR(...)  CIB_LOG_WITH_LEVEL(logging::level::ERROR __VA_OPT__(, ) __VA_ARGS__)
```

### Step 2 - the macro builds the environment type and captures the call site (`log/log.hpp:66-69`)

```cpp
#define CIB_LOG_WITH_LEVEL(LEVEL, ...)                                         \
    logging::log<                                                              \
        stdx::extend_env_t<cib_log_env_t, logging::get_level, LEVEL>>(         \
        __FILE__, __LINE__, STDX_CT_FORMAT(__VA_ARGS__))
```

Three things happen here at once, and all three are preprocessor-level:

1. `LEVEL` is lifted into a **template argument** (`stdx::extend_env_t<...>`), so the log level
   becomes part of the *type* of the call.
2. `__FILE__` and `__LINE__` capture the call site.
3. `STDX_CT_FORMAT(__VA_ARGS__)` lifts the format string into a template argument too.

### Step 3 - the format string becomes a template argument (`stdx/ct_format.hpp:446-447`)

```cpp
#define STDX_CT_FORMAT(S, ...)                                                 \
    stdx::ct_format<S>(STDX_MAP(CX_WRAP __VA_OPT__(, ) __VA_ARGS__))
```

`stdx::ct_format` is a **variable template** (`stdx/ct_format.hpp:408-410`):

```cpp
template <ct_string Fmt,
          template <typename T, T...> typename Output = detail::null_output>
constexpr auto ct_format = [](auto &&...args) { ... };
```

So the format string `S` must arrive as a *template argument*. A function call cannot put a
runtime value into a template argument position - only the preprocessor can move the token there.
**This is the one job that is genuinely macro-shaped.**

The arguments are wrapped by `CX_WRAP` (`stdx/utility.hpp:427-450`), which decides per argument
whether it is a compile-time value or a runtime value:

```cpp
#define CX_WRAP(...)                                                           \
    [&]([[maybe_unused]] auto f) {                                             \
        if constexpr (STDX_IS_TYPE(__VA_ARGS__)) {                             \
            return ::stdx::type_identity<__typeof__(__VA_ARGS__)>{};           \
        } else if constexpr (::stdx::is_cx_value_v<...> or ...) {              \
            return f();                                                        \
        } else if constexpr (decltype(::stdx::cxv_detail::cx_detect(f))::value) { \
            return ::stdx::overload{::stdx::cxv_detail::cx_base{}, f};         \
        } else {                                                               \
            return f();                                                        \
        }                                                                      \
    }([&] { return (__VA_ARGS__) + ::stdx::cxv_detail::type_val{}; }())
```

The `+ type_val{}` forces constant evaluation, so an argument that *can* be constant-evaluated
becomes a `cx_value` and is folded into the format string at compile time; one that cannot stays
a runtime value. `stdx::ct_format` then checks the counts:

```cpp
static_assert(data::N == sizeof...(args),
              "Format string has a mismatch between the number of format "
              "specifiers and arguments.");
```

(`stdx/ct_format.hpp:416-418`). In `src/app.cpp:27-28`, `answer` is `constexpr`, so it is folded
into the string and the *type* of the message is what the catalog tooling sees.

### Step 4 - the call is an ordinary function template (`log/log.hpp:54-58`)

```cpp
template <typename Env, typename... Ts, typename... TArgs>
static auto log(TArgs &&...args) -> void {
    auto &cfg = get_config<Env, Ts...>();
    cfg.logger.template log<Env>(std::forward<TArgs>(args)...);
}
```

**This is the key structural fact: from here on, everything is a template.** The environment
`Env` carries the level and the module name in its type; `get_config<Env, Ts...>()`
(`log/log.hpp:44-52`) selects the implementation.

### Step 5 - the project's implementation (`include/cpp-core/logging/cib_quill.hpp:127-163`)

```cpp
struct quill_config {
  struct {
    template <typename Env, typename File, typename Line, typename FR>
    auto log(File file, Line line, FR const &fr) const -> void {
      constexpr auto level = to_quill_level(level_of(::logging::get_level(Env{})));
      fr.args.apply([&]<typename... Args>(Args &&...args) {
        using Message = message_type_t<decltype(fr.str), std::remove_cvref_t<Args>...>;
        using Module = module_type_t<Env>;
        auto const string_id = ::catalog<Message>();
        auto const module_id = ::module<Module>();
        ...
        quill_logger()->template log_statement_runtime_metadata<true>(
          &metadata, fmt.c_str(), file, "", tags.c_str(), static_cast<std::uint32_t>(line), level,
          decay_enum_value(std::forward<Args>(args))...);
      });
    }
  } logger;
};
```

The catalog IDs are assigned at build time by the `gen_str_catalog()` tooling, and the message's
**type** is the catalog key (`message_type_t<decltype(fr.str), ...>`). That is the "binary logger"
design: the format string and the compile-time arguments are part of the type, so no string data
ends up in the payload.

### Step 6 - the module declaration (`log/module.hpp:28`, `log/env.hpp:10-13`)

```cpp
#define CIB_LOG_MODULE(S) CIB_LOG_ENV(logging::get_module, stdx::shrink<S>())
```

```cpp
#define CIB_LOG_ENV_DECL(...)                                                  \
    [[maybe_unused]] typedef decltype([] {                                     \
        return stdx::extend_env_t<cib_log_env_t, __VA_ARGS__>{};               \
    }()) cib_log_env_t
```

`CIB_LOG_MODULE("cpp_core")` declares a `cib_log_env_t` in the enclosing namespace that **shadows**
the global alias `using cib_log_env_t = stdx::env<>;` (`log/env.hpp:6`). The module name
`stdx::shrink<"cpp_core">()` becomes part of the environment type, and the catalog tooling reads
it back out (`cib_quill.hpp:108-116`).

## 2. Which steps are impossible without a macro - and which are not

| Job the macro does | Impossible *as written*? | The macro-free equivalent | Cost |
|---|---|---|---|
| Lift the format string into a template argument | **yes, as written** - a runtime value cannot become a template argument | write `stdx::ct_format<"the format">(args...)` yourself | the format string moves from an argument position to a template position; the caller must know `stdx` |
| Put the level into the environment type | **yes, as written** | write `stdx::extend_env_t<cib_log_env_t, logging::get_level, logging::level::INFO>` yourself | long and noisy; one line per level |
| Capture the call site (`__FILE__`, `__LINE__`) | **yes, as written** - these are preprocessor tokens | `std::source_location::current()` as a default argument | **none in the cib path** (it is not standard-library-free); blocked in the module path |
| Declare the module environment | **yes, as written** | a `using` alias in the enclosing namespace | one line instead of one macro; equivalent |
| Select the implementation | **no** - already a template | `logging::config<Env>` | - |
| Fold the compile-time arguments into the format string | **no** - `stdx::ct_format` does it | `stdx::ct_format` | - |
| Assign the catalog IDs | **no** - the build tooling does it | `::catalog<Message>()` | - |

**So the answer to "is there a macro-free equivalent of the binary-logger path in cib?" is yes:**

```cpp
// macro-free, same code path, same catalog IDs
using cib_log_env_t =
    stdx::extend_env_t<::cib_log_env_t, logging::get_module, stdx::shrink<"cpp_core">()>{};

logging::log<stdx::extend_env_t<cib_log_env_t, logging::get_level, logging::level::INFO>>(
    std::source_location::current().file_name(),
    std::source_location::current().line(),
    stdx::ct_format<"compile-time formatted: the answer is {}">(answer));
```

That reaches `logging::log<Env>` -> `get_config<Env>()` -> `quill_config::logger::log<Env>` -> the
same `catalog<Message>()` call, so **the string catalog still works**. The macros are not load-bearing
for the catalog; they are load-bearing for *readability*.

## 3. The options

| # | Option | Macros before / after | What it costs | Verdict |
|---|---|---|---|---|
| a | **Keep the CIB macros as they are** | 4 / 4 | nothing | **keep** |
| b | Route the application through the project's own macro-free module path | 4 / 0 | **loses the string catalog entirely** - the binary logger is the point of the cib path | **drop** |
| c | Keep the catalog, spell the calls out in templates | 4 / 0 | each log call becomes two long template expressions; the compile-time-argument folding becomes the caller's problem | **do later, if ever** |
| d | Use C++26 reflection to derive the catalog IDs or the format strings | 4 / 4 | impossible: reflection ranges allocate and cannot be walked in a constant expression, and the catalog IDs are assigned by the build tooling, not by the language | **drop** |
| e | Use `std::source_location` for the call-site capture in the cib path | 4 / 4 | nothing in the cib path; it already includes `<string>`, `<string_view>` and `<type_traits>` | **do later - it is cheap** |
| f | Use `stdx::ct_format` / `stdx::ct_string` in place of the module's hand-rolled scanner | 4 / 4 | **impossible inside the module interface** - see section 4 | **drop** |

### On option (b) in detail

The module path (`modules/logging/logging.cppm`) is already macro-free and already has a
compile-time format-string check. Routing the application through it would delete the four macro
invocations *and* the whole cib machinery - but it would also delete:

- the **string catalog** (`cmake/catalog.cmake`, the `gen_str_catalog()` tooling, the `catalog<>` and
  `module<>` symbol scan of the object files) - which is a feature, not an implementation detail;
- the **binary logger** property: in the module path the format string ends up as *data* in the
  message; in the cib path it is part of the message's *type* and never reaches the binary.

That is a large functional loss for a small syntactic gain. **Drop.**

### On option (c) in detail

It is technically sound (section 2) and it keeps the catalog. It is not recommended, because the
whole point of `CIB_INFO` is that it reads like a function call:

```cpp
CIB_INFO("compile-time formatted: the answer is {}", answer);
```

versus

```cpp
logging::log<stdx::extend_env_t<cib_log_env_t, logging::get_level, logging::level::INFO>>(
    loc.file_name(), loc.line(), stdx::ct_format<"compile-time formatted: the answer is {}">(answer));
```

Three log calls in `src/app.cpp` do not justify that. **Do later, if ever** - and if the project
ever grows a second macro-free logging idiom, option (c) is the way to converge.

### On option (e) - the cheap one

`std::source_location::current()` used in a default argument returns the **call site's** location,
which is exactly the trick the module path already uses with the defaulted
`__builtin_FILE` / `__builtin_LINE` / `__builtin_FUNCTION` parameters
(`modules/logging/logging.cppm:64-83, 101-105`).

The module path cannot use `std::source_location` because its interface must not name
`<source_location>`. **The cib path has no such restriction** - `include/cpp-core/logging/cib_quill.hpp`
already includes `<string>`, `<string_view>`, `<type_traits>` and `<utility>`. So the `__FILE__` /
`__LINE__` pair that the macro passes could be replaced by a `std::source_location` default
argument on `quill_config::logger::log`, and the macro would then only have to supply the format
string and the level.

This is a **small, contained improvement**: it removes the macro's need to touch the call site at
all, and it makes the project use one idiom for source-location capture on both paths. It is worth
doing when the build lane reopens, and it is not worth a macro-reduction project on its own.

**And there is a second thing option (e) would fix** - found by part 20, which read the catalog
path line by line. **The catalog path carries no function name at all.**
`quill::Logger::log_statement_runtime_metadata` takes the function name as its **fourth**
parameter (`quill/Logger.h:427-433`), and the module path passes the real one
(`src/logging/quill_logger.cpp:117-118`: `file, function`). The catalog path passes an **empty
string** (`include/cpp-core/logging/cib_quill.hpp:157-159`: `file, ""`).

The cause is upstream: cib's `CIB_LOG` hands the customization point only the file and the line
(`log/log.hpp:63-64`):

```cpp
#define CIB_LOG(...) \
    logging::log<cib_log_env_t>(__FILE__, __LINE__, STDX_CT_FORMAT(__VA_ARGS__))
```

There is no function name in the interface, so there is none to pass. **No visible effect today** -
the project's pattern prints `%(short_source_location)`, not `%(caller_function)`
(`src/logging/quill_logger.cpp:33-35`) - but quill's `%(caller_function)` attribute would show the
module path's function and nothing at all for the catalog path.

`std::source_location::current()` carries the function name as well as the file and the line, so
option (e) fixes this too. That makes option (e) worth more than it looked: it is not only "the
cheap one", it is the one that makes the two paths agree on the call site.

## 4. The decisive detail: `stdx` is not usable inside the module interface

The most promising replacement for the module's hand-rolled compile-time scanner
(`scan_format`, `format_matches`) was Intel's own constexpr formatting. **It cannot be used
there.** The include lists, read directly from the installed headers:

**`stdx/ct_string.hpp:8-14`**

```cpp
#include <array>
#include <concepts>
#include <cstddef>
#include <iterator>
#include <string_view>
#include <type_traits>
#include <utility>
```

**`stdx/ct_format.hpp:16-24`**

```cpp
#include <boost/mp11/algorithm.hpp>

#include <algorithm>
#include <array>
#include <cstddef>
#include <iterator>
#include <string_view>
```

(plus `stdx/detail/fmt.hpp`, which pulls in **fmt** itself)

**`stdx/type_traits.hpp:6-11`**

```cpp
#include <boost/mp11/algorithm.hpp>

#include <array>
#include <cstddef>
#include <type_traits>
#include <utility>
```

`stdx/ct_string.hpp` is the one the module would need most, and it pulls in seven standard
headers. `stdx/ct_format.hpp` adds `<algorithm>`, fmt and Boost.MP11.

The module interface's global module fragment is attached to the global module, and a standard
header included there collides with the importing translation unit's own standard headers (the
errors are quoted at `modules/logging/logging.cppm:9-19`: GCC's "redefinition of 'constexpr bool
std::__is_constant_evaluated()'" and Clang's "type alias template redefinition with different
types ('std::__promote_t')"). **So `stdx` cannot be used inside the module interface, and with it
goes the idea of replacing the hand-rolled scanner with Intel's constexpr formatter.**

For completeness, `stdx/ct_string.hpp` is exactly what the **cib** path uses - and the cib path is
not standard-library-free, so that is fine there.

## 5. What this means for the module's own constructs

| Module construct | Reachable by a macro-free, template-only rewrite? | Reachable by reflection? | Reachable by `stdx`? |
|---|---|---|---|
| `scan_format` / `format_matches` (the consteval scanner) | yes - but it is already a `consteval` function with no macro in it | **no** - reflection does not operate on string-literal contents | **no** - `stdx` pulls standard headers into the module |
| the compile-time type traits (`is_same`, `remove_cvref_t`, ...) | yes - they are plain templates already | **no** - reflection is not a type-category facility | **no** - same reason |
| the `__builtin_FILE` / `__builtin_LINE` / `__builtin_FUNCTION` default arguments | already macro-free | - | - |
| `std::source_location` for the call site | yes - but only if the module may name `<source_location>` | - | - |

**None of this needs a macro, and none of it needs reflection.** The module path is already the
model: a `consteval` function for the compile-time check, templates for the traits, and default
arguments for the call site.

## 6. The recommendation

**Keep the CIB macros.** The project gets the string catalog, the compile-time argument folding
and the binary-logger design from them, and the macro-free spelling of the same calls is
substantially noisier at every call site. There is no macro-free equivalent that is *better*, only
one that is *different*.

Three small, worthwhile things, in order:

1. **Use `std::source_location` in the cib path's call-site capture** (option (e)). The cib path is
   not standard-library-free, so this costs nothing, and it makes the project use one source-location
   idiom on both paths. It also reduces the macro's job to "supply the format string and the level".
2. **Keep the module path macro-free** - it already is, and the audit found no macro in it.
3. **Do not touch the reflection story for the logging path.** The blockers are the same ones as
   for the formatter: no constexpr allocation, and the module interface may not name the standard
   library.

## 7. Open questions

1. Does `std::source_location::current()` in a default argument on
   `quill_config::logger::log` return the **caller's** location? It should - the default argument
   is evaluated at the call site - but the call goes through `logging::log<Env>`, which is a
   template, so the "call site" is the `logging::log` invocation inside the macro, not the user's
   line. **This needs a compile to settle, and it may be the reason the macro cannot be dropped.**
   (The module path's `__builtin_FILE` default arguments work because the defaulted parameter is
   evaluated where the *caller* writes the call; the equivalent here would be a defaulted parameter
   on `logging::log` itself, which Intel's headers do not offer.)
2. Does the catalog tooling's `nm` scan still find the same undefined `catalog<>` / `module<>`
   symbols if the calls are written macro-free? The mangling of the specializations is unaffected
   in theory, but this needs a measurement.
3. Would `std::format_string<Args...>` accept the format strings the project uses today? The
   module's scanner rejects named arguments and a bare `}` (`format.hpp:239-241, 270`), and
   `std::format_string` rejects a few things the hand-rolled scanner accepts. The two dialects are
   not identical, and the difference has to be enumerated before any switch.
