# Quill's runtime formatting, the type-erasure boundary, and a live defect

**Date:** 2026-11-11
**Status:** research. Nothing here is applied to the build.

## The question

cpp-core has two logging paths that format differently:

- the **module path** (`modules/logging/logging.cppm`) has no macro, so it hand-rolls a
  printf-style formatter inside its module interface (`modules/logging/format.hpp`, 602 lines),
  formats the message itself into a fixed 2048-byte buffer, and hands quill an
  **already-formatted** message with the format string `"{}"`
  (`src/logging/quill_logger.cpp:117-118`);
- the **cib path** (`include/cpp-core/logging/cib_quill.hpp`) hands quill the format string **and**
  the runtime arguments, and quill formats on its backend thread (`cib_quill.hpp:157-159`).

If quill could format from a runtime format string and runtime arguments, the hand-rolled
formatter could shrink dramatically - provided the arguments can cross the module's
standard-library-free boundary.

## The answers

**1. Yes - quill formats from a runtime format string, and cpp-core is already calling that
function.**

```cpp
// quill/Logger.h:426-431
template <bool enable_immediate_flush, typename... Args>
QUILL_ATTRIBUTE_HOT bool log_statement_runtime_metadata(MacroMetadata const* macro_metadata,
                                                        char const* fmt, char const* file_path,
                                                        char const* function_name, char const* tags,
                                                        uint32_t line_number, LogLevel log_level,
                                                        Args&&... fmt_args)
```

`fmt` at `Logger.h:428` is an ordinary runtime `char const*`. It is forwarded verbatim to
`fmtquill::vformat_to` on the backend thread (`backend/BackendWorker.h:2415-2417`). Quill's own
macro-free function API (`quill/LogFunctions.h:225-243`) is a thin wrapper over the same function,
and is explicitly documented for runtime format strings
(`docs/macro_free_mode.rst:47-58`).

**2. Quill has no compile-time format-string check to lose.** A search of the whole of `quill/`
(excluding `bundled/fmt`) for `fmtquill::format_string`, `FMTQUILL_STRING` and
`compile_format_string` returns **zero hits**. The macro path passes the literal through
`MacroMetadata` as a plain `char const*` (`LogMacros.h:390`), and the runtime path takes a plain
`char const*` (`Logger.h:428`). The only compile-time errors quill emits are about the *argument
types* (a missing `Codec` - `core/Codec.h:199, 276, 317, 352`). A malformed format string surfaces
only on the backend, as a `[Could not format log statement...]` line
(`BackendWorker.h:2432-2452`) - it is never thrown to the caller.

**This matters:** cpp-core's own `consteval` check (`logging.cppm:66-76`) is *strictly stronger*
than anything quill does, and it is independent of who does the formatting. Moving the rendering
to quill does not weaken it.

**3. The type erasure is already half done - and it is not the blocker.**

The module already erases the argument types across the boundary, as two parallel tables of
function pointers and addresses (`format.hpp:537-540`):

```cpp
using formatter_fn = unsigned long (*)(void const *, field_spec &, char *, unsigned long) noexcept;
formatter_fn const formatters[] = {&format_value<remove_cvref_t<Args>>...};
void const *const values[] = {argument_value(args)...};
```

The blocker is not erasure. It is that quill's runtime formatter consumes a **compile-time-typed
variadic pack**.

**4. A custom `quill::Codec` is the way through it.** `Codec<Arg>` is an open extension point -
`template <typename Arg, typename = void> struct Codec` (`core/Codec.h:164-165`), documented as
"Writing Custom Codec" (`docs/recipes.rst:637`). The codec's `decode_and_store_arg` can push as
many arguments into the store as it likes, and **the argument count is taken from the store, not
from the pack**:

```cpp
// backend/BackendWorker.h:2411-2417
int const user_arg_count = _format_args_store.size() - ...;
basic_format_args{_format_args_store.data(), user_arg_count}
```

The decoder is reached through `detail::decoder_ptr<Args...>` (`Codec.h:421`) and recovered as a
`void(*)(std::byte*&, DynamicFormatArgStore&)` (`Codec.h:412`, `BackendWorker.h:1021-1023`). One
pack element therefore means exactly one decoder, whatever the arity - no combinatorial template
explosion, no per-arity switch.

The shape would be:

```cpp
// ---- implementation side (src/logging/), may use quill and the standard library ----

struct arg_blob {                 // one pack element, handed to quill
  erased_list const *args;
  unsigned count;
  char const *tmpl;
};

template <> struct quill::Codec<arg_blob> {
  static size_t compute_encoded_size(detail::SizeCacheVector &, arg_blob const &) noexcept;
  static void encode(std::byte *&, detail::SizeCacheVector const &, uint32_t &, arg_blob const &) noexcept;
  static void decode_and_store_arg(std::byte *&, DynamicFormatArgStore *) noexcept;
};
```

One caveat, from the source: `DeferredFormatCodec`'s fast path is
`memcpy(buffer, &arg, sizeof(arg))` (`DeferredFormatCodec.h:135-137`), which would copy a
**pointer** into a ring buffer that outlives the caller's stack. The blob codec must **not** derive
from `DeferredFormatCodec`; it must write the bytes itself.

**No quill codec does this today, and the documentation does not promise it.** It is a one-step
extrapolation of a documented extension point. That single step is the only thing in this document
that genuinely needs a compile to confirm.

## The defect this turned up

**`set_level()` does not filter anything on the module path.**

The chain, read from the installed quill 13.1.0 headers:

| Step | Where | What it does |
|---|---|---|
| `set_log_level(int)` | `src/logging/quill_logger.cpp:101` | calls `quill_logger()->set_log_level(...)` |
| `Logger::set_log_level` | `quill/core/LoggerBase.h:142-150` | stores the threshold in the **logger's** `_log_level` |
| `should_log_statement` | `quill/core/LoggerBase.h:178, 188` | the only reader of that threshold: `log_statement_level >= get_log_level()` |
| quill's macro wrapper | `quill/LogMacros.h:404` | calls it before logging |
| quill's function wrapper | `quill/LogFunctions.h:75` | calls it before logging |
| **cpp-core's `emit()`** | **`src/logging/quill_logger.cpp:117`** | **calls `log_statement_runtime_metadata` directly, with no check** |
| the backend | `quill/backend/BackendWorker.h:1500` | filters against each **sink's** threshold, not the logger's |
| the sink's default | `quill/sinks/Sink.h:279` | `std::atomic<LogLevel> _log_level{LogLevel::TraceL3}` - everything passes |

`Logger::set_log_level` does not touch the sinks, and the sink's threshold is what the backend
applies. So the logger threshold that `set_level()` sets is read by nobody on this path, and the
sink's threshold stays at `TraceL3`.

**Consequence:** a message logged below the configured level is still emitted. `set_level(level::error)`
does not suppress the `info` messages.

This is a live defect, not a trade-off, and it is worth fixing whatever else happens:

- the **module path** needs the check in `emit()` - `if (logger->should_log_statement(level))` before
  `log_statement_runtime_metadata`, which is exactly what quill's own function wrapper does at
  `LogFunctions.h:75`; or the sink's filter needs to be set instead of the logger's;
- the **cib path** (`cib_quill.hpp:157-159`) has the same shape - it calls
  `log_statement_runtime_metadata` directly, with no check - so the same fix applies there;
- `quill::detail::log` (`LogFunctions.h:63-83`) is the reference implementation, and it is a
  drop-in for both call sites.

The existing test suite cannot catch this: the tests set the level and read it back
(`logging_test.cpp:74-81`), but they never assert that a message *below* the threshold is
suppressed. That assertion belongs in the coverage work (see
[coverage-gaps.md](coverage-gaps.md), section 1) - "level filtering" is on the uncovered list
precisely because it does not work.

**A second thing the same call site gets wrong** - found by part 20, which read the file line by
line. `quill::Logger::log_statement_runtime_metadata` takes the function name as its **fourth**
parameter (`quill/Logger.h:427-433`). The module path passes the real one
(`src/logging/quill_logger.cpp:117-118`: `file, function`); the catalog path passes an **empty
string** (`include/cpp-core/logging/cib_quill.hpp:157-159`: `file, ""`). The cause is upstream -
cib's `CIB_LOG` hands the customization point only `__FILE__` and `__LINE__`
(`log/log.hpp:63-64`) - so there is no function name to pass. It has no visible effect today,
because the project's pattern prints `%(short_source_location)` and not `%(caller_function)`
(`src/logging/quill_logger.cpp:33-35`), but quill's `%(caller_function)` attribute would show the
module path's function and nothing at all for the catalog path. Part 6's option (e) fixes it.

## The three options

### (a) The formatter stays

- **Pro:** zero risk; the behaviour is frozen; the consteval check and the formatter are one
  self-contained, standard-library-free unit; the 2048-byte truncation contract is explicit.
- **Con:** `format.hpp` is compiled into every importing translation unit
  (`format.hpp:4-6`); `emit()` heap-allocates a `std::string` per call for every message over 22
  bytes (`quill_logger.cpp:118`) and burns about 3 KiB of stack (`format.hpp:204`, `format.hpp:580`);
  the truncation is **silent**; the cib path and the module path are two formatting engines for one
  library.
- **Work:** none.

### (b) Shrink to a thin adapter: hand quill the format string and a type-erased argument list

- **Pro:** the formatting work leaves the caller entirely - no per-call `std::string`, no 3 KiB of
  stack, no caller-side truncation, no code in the importing translation unit; one formatting engine
  for both paths; the silent 2047-byte cap disappears.
- **Con:** it depends on a custom `quill::Codec` that pushes *N* arguments from one pack element -
  an extrapolation of a documented extension point, not documented practice. The `self_formatting`
  path (a type with its own `format_to` member) cannot be pushed as a fmt argument at all, because
  the member only exists in the importing translation unit and the backend cannot call it - those
  fields would have to be pre-formatted on the frontend, which forces the template to be rewritten
  at compile time. And the format string would have to be NUL-terminated for quill's `safe_strnlen`
  (`Logger.h:475`), which the module's `format_string` does not currently promise.
- **Risk:** the highest of the three. The multi-argument codec is unverified. The float rendering
  changes for the default specification - the module's `%g` gives six significant digits, fmt gives
  the shortest round-trip, so `0.1`, `1.0/3.0`, `1e-7`, `1e20` and the infinities all render
  differently. And messages over 2047 bytes would go from silently truncated to emitted in full.
- **Work:** roughly 300-380 new lines in the implementation (the blob, the codec, the decode
  walker), roughly 330-400 lines deleted from `format.hpp`, and roughly 90 lines changed in the
  module and the internal interface. Net LOC-neutral, but it *moves* that code out of every
  importing translation unit.

### (c) Delete the formatter and move the formatting behind the `emit()` boundary

- **Pro:** the smallest diff of the three; one formatting engine; `format.hpp` disappears from the
  importing translation units; the module keeps its compile-time `format_string` check untouched.
- **Con:** **it collapses into (b).** The argument types have to be named at the call site to be
  forwarded, and the boundary (`include/cpp-core/logging/internal.hpp`) is a plain
  non-template interface - so the module has to build the same erased blob anyway. The genuine
  version of (c) is "the module erases to a blob, and the implementation renders it and hands
  quill already-formatted text" - which keeps a hand-rolled formatter, only relocated. That is
  strictly worse than (b) with strictly more work.

## The recommendation

**Option (b), gated on one experiment.**

The experiment: a scratch translation unit that instantiates
`log_statement_runtime_metadata<true>` with a *single* pack element whose `Codec` pushes three
primitives, and asserts that the rendered line reads `1 2 3`. If that works - and the reads at
`BackendWorker.h:2411-2417` and `Codec.h:412-421` say it must - then (b) buys about 400 lines of
deletion, one formatting engine, and no caller-side allocation, for about 350 lines of addition.

If it does not work, (a) with the `%g` comment corrected is the honest resting place.

**Whatever option is chosen, the level-filtering defect must be fixed.** It is a bug, not a
trade-off, and the fix is three lines in each of the two call sites.

## The open questions

1. Does a `Codec` that pushes three arguments from one pack element satisfy a `"{} {} {}"`
   statement? This is the load-bearing unknown for option (b).
2. Which types can be pushed into `DynamicFormatArgStore` without a formatter - `bool`, `char`, the
   signed and unsigned 8/16/32/64-bit integers, `float`, `double`, `long double`, `void const *`,
   `string_view`? And does a scoped `enum` push as its underlying integer, or does it need a
   formatter? (The cib path already has a `decay_enum_value` helper at `cib_quill.hpp:55-61` for
   this reason.)
3. Exactly which default-specification outputs change between the module's `snprintf("%g")` and
   fmt's shortest round-trip?
4. Does fmt render the whole specification cross-product identically to the module's `parse_spec` -
   in particular `#` with `b`/`x`/`o`, `0` padding combined with a sign, `^` centring, and
   precision on a string (fmt truncates; the module clamps in `copy_text`, `format.hpp:300-312`)?
5. Can the module's `format_string` hold a compile-time-rewritten template - a struct with a
   `char[N]` member and no standard-library types - so that the pre-formatted fields become `{}`
   and the pass-through fields keep their specification? This is what the `self_formatting` path
   needs.
6. Will the compiler accept a `char const[N]` with no terminator at the `consteval format_string`
   boundary (`logging.cppm:67`)? If it will, option (b) introduces an out-of-bounds read in
   quill's `safe_strnlen` that is impossible today, and the consteval check would have to require
   `text[N-1] == '\0'`.
7. Does a message over 2047 bytes behave acceptably on the default `UnboundedBlocking` queue, and
   would a bounded queue throw `QuillError` (`Logger.h:871-882`) where the message is silently
   truncated today?
8. `emit()` hard-codes `<true>` for the immediate-flush template parameter
   (`quill_logger.cpp:117`). Should the module path flush on every message, or match quill's
   macro-free default? That is a throughput decision and needs a measurement, not a guess.
