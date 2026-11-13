# Intel Libraries Dependency Analysis

## 1. Header Inventory by Library

### 1.1 `intel-cib` (compile-time-init-build)

| Category | Headers (under `include/`) |
|----------|---------------------------|
| **Root** | `cib/cib.hpp`, `cib/top.hpp` |
| **Flow DSL** | `flow/builder.hpp`, `flow/debug_builder.hpp`, `flow/dsl/par.hpp`, `flow/dsl/seq.hpp`, `flow/dsl/subgraph_identity.hpp`, `flow/dsl/walk.hpp`, `flow/flow.hpp`, `flow/func_list.hpp`, `flow/graph_builder.hpp`, `flow/graph_common.hpp`, `flow/log.hpp`, `flow/run.hpp`, `flow/service.hpp`, `flow/step.hpp`, `flow/viz_builder.hpp` |
| **Interrupt** | `interrupt/concepts.hpp`, `interrupt/config.hpp`, `interrupt/dynamic_controller.hpp`, `interrupt/fwd.hpp`, `interrupt/impl.hpp`, `interrupt/manager.hpp`, `interrupt/policies.hpp` |
| **Logging (text)** | `log/README.md`, `log/env.hpp`, `log/flavor.hpp`, `log/level.hpp`, `log/log.hpp`, `log/module.hpp`, `log/unit.hpp` |
| **Logging (binary)** | `log_binary/catalog/arguments.hpp`, `log_binary/catalog/builder.hpp`, `log_binary/catalog/catalog.hpp`, `log_binary/catalog/encoder.hpp`, `log_binary/catalog/mipi_builder.hpp`, `log_binary/catalog/mipi_messages.hpp`, `log_binary/catalog/writer.hpp`, `log_binary/module_id.hpp`, `log_binary/string_id.hpp`, `log_binary/tags.hpp` |
| **Logging (fmt-based)** | `log_fmt/logger.hpp` |
| **Lookup** | `lookup/detail/select.hpp`, `lookup/entry.hpp`, `lookup/input.hpp`, `lookup/linear_search_lookup.hpp`, `lookup/lookup.hpp`, `lookup/pseudo_pext_lookup.hpp`, `lookup/strategies.hpp`, `lookup/strategy_failed.hpp` |
| **Match** | `match/and.hpp`, `match/bin_op.hpp`, `match/concepts.hpp`, `match/constant.hpp`, `match/cost.hpp`, `match/implies.hpp`, `match/negate.hpp`, `match/not.hpp`, `match/ops.hpp`, `match/or.hpp`, `match/predicate.hpp`, `match/simplify.hpp`, `match/sum_of_products.hpp` |
| **Message** | `msg/callback.hpp`, `msg/detail/indexed_builder_common.hpp`, `msg/detail/indexed_handler_common.hpp`, `msg/detail/separate_sum_terms.hpp`, `msg/field.hpp`, `msg/field_matchers.hpp`, `msg/handler.hpp`, `msg/handler_builder.hpp`, `msg/handler_interface.hpp`, `msg/indexed_builder.hpp`, `msg/indexed_handler.hpp`, `msg/indexed_service.hpp`, `msg/message.hpp`, `msg/message_destructure.hpp`, `msg/send.hpp`, `msg/service.hpp` |
| **Nexus** | `nexus/callback.hpp`, `nexus/conditionals.hpp`, `nexus/config.hpp`, `nexus/detail/components.hpp`, `nexus/detail/config_details.hpp`, `nexus/detail/config_item.hpp`, `nexus/detail/constexpr_conditional.hpp`, `nexus/detail/exports.hpp`, `nexus/detail/extend.hpp`, `nexus/detail/nexus_details.hpp`, `nexus/detail/runtime_conditional.hpp`, `nexus/extend.hpp`, `nexus/func_decl.hpp`, `nexus/nexus.hpp`, `nexus/service.hpp` |
| **Sequence** | `seq/builder.hpp`, `seq/impl.hpp`, `seq/step.hpp` |

### 1.2 `intel-cpp-std-extensions` (`stdx::`)

| Header | Primary Contents |
|--------|-----------------|
| `algorithm.hpp` | Algorithms on tuples/ranges (not read) |
| `array.hpp` | `stdx::array` — fixed-capacity array with `constexpr` ops |
| `atomic.hpp` | `stdx::atomic` wrapper, `atomic_ref` |
| `atomic_bitset.hpp` | Lock-free atomic bitset |
| `bit.hpp` | **All of `<bit>`**: `endian`, `bit_cast`, `byteswap`, `countl_zero`, `countr_zero`, `popcount`, `rotl`, `rotr`, `has_single_bit`, `bit_width`, `bit_ceil`, `bit_floor`, `bit_mask`, `bit_pack`, `bit_unpack`, `bit_destructure`, `bit_structure` — **all `constexpr`** |
| `byterator.hpp` | Byte iterator adaptor |
| `cached.hpp` | `cached` — memoization wrapper |
| `call_by_need.hpp` | `call_by_need` — lazy evaluation |
| `compiler.hpp` | Compiler detection, `STDX_PRAGMA`, `always_false_v` |
| `concepts.hpp` | **All C++20 concepts** (backported if missing): `floating_point`, `integral`, `signed_integral`, `unsigned_integral`, `convertible_to`, `derived_from`, `same_as`, `equality_comparable`, `totally_ordered`, `invocable`, `predicate`, plus `same_as_unqualified`, `callable`, `has_trait`, `structural`, `complete`, `same_template_as`, `tuple_comparable`, `tuplelike`, `has_tuple_protocol`, `has_array_protocol` |
| `ct_conversions.hpp` | `type_as_string()`, `enum_as_string()`, `template_base()` — **compile-time type/value reflection via `__PRETTY_FUNCTION__`** |
| `ct_format.hpp` | **Compile-time `fmt`-compatible formatting**: `ct_format<Fmt>(args...)`, `format_result`, `named_arg`, `make_format_result`, `num_fmt_specifiers`, `STDX_CT_FORMAT` macro — **fully `constexpr`** |
| `ct_string.hpp` | **`ct_string<N>`** — fixed-capacity compile-time string, `cts_t`, `shrink()`, `with_name`, `matching_name`, `operator""_cts`, `operator""_ctst` — **fully `constexpr`** |
| `cx_map.hpp` | Compile-time map |
| `cx_multimap.hpp` | Compile-time multimap |
| `cx_queue.hpp` | Compile-time queue |
| `cx_set.hpp` | Compile-time set |
| `cx_vector.hpp` | Compile-time vector |
| `detail/bitset_common.hpp` | Shared bitset implementation |
| `detail/fmt.hpp` | Internal fmt helpers |
| `detail/freestanding.hpp` | Freestanding compatibility |
| `detail/list_common.hpp` | Shared list implementation |
| `env.hpp` | **`env<Props...>`** — compile-time environment with `extend_env_t`, `append_env_t`, `query()` — **fully `constexpr`** |
| `for_each_n_args.hpp` | Variadic `for_each` |
| `function_traits.hpp` | `args_t`, `return_t`, `function_traits` |
| `functional.hpp` | `overload`, `bind_front`, `bind_back`, `unary_plus`, `safe_identity`, `dereference`, `with_result_of` — **`constexpr`** |
| `intrusive_forward_list.hpp` | Intrusive forward list |
| `intrusive_list.hpp` | Intrusive list |
| `iterator.hpp` | Iterator utilities |
| `latched.hpp` | `latched` — one-time initialization |
| `meta.hpp` | Meta-programming utilities |
| `numeric.hpp` | Numeric algorithms |
| `optional.hpp` | `stdx::optional` — `constexpr` optional |
| `panic.hpp` | `panic_handler`, `panic<Ts...>()`, `STDX_PANIC` macro |
| `pp_map.hpp` | Preprocessor map utilities |
| `priority.hpp` | Priority types |
| `ranges.hpp` | Range utilities |
| `rollover.hpp` | Rollover counter |
| `span.hpp` | `stdx::span` — **`constexpr`** |
| `static_assert.hpp` | `STATIC_ASSERT` macro with message |
| `tuple.hpp` | **`stdx::tuple`**, `indexed_tuple`, `one_of`, `get`, `make_tuple`, `tuple_cat`, `apply`, `transform`, `for_each`, `join`, `fold_left`, `fold_right`, `tail` — **fully `constexpr`**, no STL dependency |
| `tuple_algorithms.hpp` | **Tuple algorithms**: `filter`, `transform`, `for_each`, `enumerate`, `all_of`, `any_of`, `none_of`, `contains_type`, `sort`, `chunk_by`, `gather_by`, `cartesian_product`, `unique`, `to_sorted_set`, `to_unsorted_set` — **all `constexpr`** |
| `tuple_destructure.hpp` | Tuple destructuring (not read) |
| `type_traits.hpp` | **Extended type traits**: `to_underlying`, `conditional_t`, `type_or_t`, `is_function_v`, `is_function_object_v`, `is_callable_v`, `type_identity`, `is_specialization_of_v`, `type_list`, `value_list`, `template_for_each`, `apply_sequence`, `is_same_unqualified_v`, `is_structural_v`, `is_cx_value_v`, `shrink/expand`, `nth_t`, `nth_v`, `tuple_size_v`, `tuple_element_t` — **fully `constexpr`** |
| `udls.hpp` | **User-defined literals**: `operator""_c`, `_lsb`/`_msb`/`_len`, `_b`/`_true`/`_false`, `_k`/`_M`/`_G`/`_ki`/`_Mi`/`_Gi`, `0_c`..`9_c` — **all `constexpr`** |
| `utility.hpp` | **Utilities**: `overload`, `unreachable()`, `type_map`/`type_pair`/`tt_pair`/`vt_pair`/`tv_pair`/`vv_pair`, `type_lookup`/`reverse_type_lookup`/`value_lookup`/`reverse_value_lookup`, `forward_like`, `as_unsigned`/`as_signed`, `sized`/`udl_sized` (`_z8`..`_z64`), `cx_value` machinery (`CX_VALUE`, `CT_WRAP`, `CX_WRAP`), `make_integer_sequence`/`make_index_sequence`, `FWD` macro |

### 1.3 `intel-baremetal-concurrency` (`conc::`)

| Header | Contents |
|--------|----------|
| `atomic.hpp` | Atomic operations (not read) |
| `concepts.hpp` | Concurrency concepts (not read) |
| `concurrency.hpp` | **`call_in_critical_section<Uniq>(F, Pred...)`** — critical section with optional predicate, policy-based (`injected_policy`), `standard_policy` using `std::mutex` when available, otherwise static_assert — **not `constexpr`** (uses `std::mutex`) |
| `detail/freestanding.hpp` | Freestanding compatibility |
| `test.hpp` | Test utilities |

### 1.4 `intel-baremetal-senders-and-receivers` (`async::`)

| Header | Contents |
|--------|----------|
| `allocator.hpp` | Allocator for async operations |
| `completes_synchronously.hpp` | `completes_synchronously_t` property |
| `completion_tags.hpp` | `set_value_t`, `set_error_t`, `set_stopped_t` |
| `compose.hpp` | Sender composition |
| `concepts.hpp` | **Full sender/receiver concepts**: `receiver`, `sender`, `sender_in`, `receiver_of`, `sender_to`, `sender_of`, `multishot_sender`, `singleshot_sender`, `scheduler`, `stoppable_sender`, `operation_state`, `queryable` |
| `connect.hpp` | `connect` CPO |
| `continue_on.hpp` | `continue_on` scheduler switching |
| `debug.hpp` / `debug_context.hpp` | Debug instrumentation |
| `env.hpp` | `empty_env`, `prop`, `get_env` |
| `forwarding_query.hpp` | Query forwarding |
| `get_completion_scheduler.hpp` | `get_completion_scheduler` |
| `get_completion_signatures.hpp` | `get_completion_signatures` |
| `get_scheduler.hpp` | `get_scheduler` |
| `incite_on.hpp` | `incite_on` |
| `into_variant.hpp` | `into_variant` sender adaptor |
| `just.hpp` | **`just`, `just_value`, `just_error`, `just_stopped`** — immediate value/error/stopped senders |
| `let.hpp` / `let_error.hpp` / `let_stopped.hpp` / `let_value.hpp` | `let` sender adaptors |
| `observe.hpp` | `observe` |
| `periodic.hpp` | Periodic sender |
| `read_env.hpp` | `read_env` |
| `repeat.hpp` | `repeat` |
| `retry.hpp` | `retry` |
| `schedulers/*.hpp` | `inline_scheduler`, `priority_scheduler`, `requeue_policy`, `runloop_scheduler`, `task`, `task_manager`, `thread_scheduler`, `time_scheduler`, `timer_manager`, `trigger_scheduler` |
| `sequence.hpp` | Sequence sender |
| `split.hpp` | `split` |
| `stack_allocator.hpp` | Stack allocator |
| `start.hpp` / `start_detached.hpp` / `start_on.hpp` | Sender launch |
| `static_allocator.hpp` | Static allocator |
| `stop_token.hpp` | Stop token |
| `sync_wait.hpp` | **`sync_wait`, `sync_wait_static`, `sync_wait_dynamic`** — blocking wait with run-loop or simple synchronizer |
| `then.hpp` | `then` sender adaptor |
| `timeout_after.hpp` | Timeout sender |
| `type_traits.hpp` | **Completion signature metaprogramming**: `completion_signatures`, `value_types_of_t`, `error_types_of_t`, `stopped_types_of_t`, `transform_completion_signatures`, `gather_signatures`, `value_holder`, `error_holder`, `stopped_holder` |
| `variant_sender.hpp` | Variant sender |
| `when_all.hpp` / `when_any.hpp` | Multi-sender combinators |

---

## 2. `intel-cib` Public API Surface (Non-Macro)

### 2.1 Core Framework (`cib::`)

```cpp
// cib/top.hpp
namespace cib {
  class EarlyRuntimeInit : public flow::service<> {};
  class RuntimeInit : public flow::service<> {};
  class RuntimeStart : public flow::service<> {};
  class MainLoop : public flow::service<> {};

  template <typename ProjectConfig>
  class top {
    constexpr static cib::nexus<component> my_nexus{};
  public:
    [[noreturn]] inline void main();  // runs EarlyRuntimeInit → RuntimeInit → RuntimeStart → MainLoop loop
    template <typename ServiceMeta>
    constexpr static auto get_service() -> auto &;  // access service by meta
  };
}

// cib/nexus/config.hpp
namespace cib {
  template <typename... Configs>
  [[nodiscard]] consteval auto config(Configs const &...configs);

  template <typename... Components>
  constexpr static detail::components<Components...> components{};

  template <typename... Services>
  constexpr static detail::exports<Services...> exports{};
}

// cib/nexus/extend.hpp
namespace cib {
  template <typename Service, typename... Args>
  [[nodiscard]] consteval auto extend(Args const &...args);
  template <stdx::ct_string Name, typename... Args>
  [[nodiscard]] consteval auto extend(Args const &...args);
  template <typename Service, typename... Args>
  [[nodiscard]] consteval auto maybe_extend(Args const &...args);
  template <stdx::ct_string Name, typename... Args>
  [[nodiscard]] consteval auto maybe_extend(Args const &...args);
}

// cib/nexus/nexus.hpp
namespace cib {
  template <typename Config>
  struct nexus {
    template <typename T>
    constexpr static auto service_v = /* initialized service */;
    template <typename T, typename... Args>
    constexpr static auto service(Args &&...args);
    template <stdx::ct_string Name, typename... Args>
    constexpr static auto service(Args &&...args);  // by name
    static auto init() -> void;  // initializes all services
  };
}

// cib/nexus/service.hpp
// Service registration and interface binding (internal machinery)
```

### 2.2 Text Logging (`logging::`)

```cpp
// log/level.hpp
namespace logging {
  enum struct level : std::uint8_t {
    MAX = 0, FATAL = 1, ERROR = 2, WARN = 3,
    INFO = 4, USER1 = 5, USER2 = 6, TRACE = 7
  };
  constexpr inline struct get_level_t { /* query */ } get_level;
}

// log/module.hpp
namespace logging {
  constexpr inline struct get_module_t { /* query */ } get_module;
}

// log/env.hpp
using cib_log_env_t = stdx::env<>;
#define CIB_LOG_ENV(...)  // extends the log environment

// log/log.hpp
namespace logging {
  template <typename Env, typename... Ts>
  constexpr static auto get_config() -> auto &;

  template <typename Env, typename... Ts, typename... TArgs>
  static auto log(TArgs &&...args) -> void;  // core logging entry point

  template <stdx::ct_string Fmt, typename Env, typename F, typename L>
  [[nodiscard]] constexpr auto panic(F file, L line, auto &&...args);  // constexpr panic with format
}

// Macros (the binary logger path):
#define CIB_LOG(...)          logging::log<cib_log_env_t>(__FILE__, __LINE__, STDX_CT_FORMAT(__VA_ARGS__))
#define CIB_LOG_WITH_LEVEL(L, ...)
#define CIB_TRACE(...)        CIB_LOG_WITH_LEVEL(level::TRACE, ...)
#define CIB_INFO(...)         CIB_LOG_WITH_LEVEL(level::INFO, ...)
#define CIB_WARN(...)         CIB_LOG_WITH_LEVEL(level::WARN, ...)
#define CIB_ERROR(...)        CIB_LOG_WITH_LEVEL(level::ERROR, ...)
#define CIB_FATAL(MSG, ...)   logging::panic<MSG, ...>(__FILE__, __LINE__, ...)
#define CIB_ASSERT(expr, ...) ((expr) ? void(0) : CIB_FATAL(...))
#define CIB_LOG_MODULE(S)     CIB_LOG_ENV(get_module, stdx::shrink<S>())
#define CIB_LOG_VERSION()     // logs version info
```

**The level scale, and the mapping the project gets wrong.** cib's levels follow the MIPI Sys-T
severity scale: **0 is the most severe** and 7 the least. Quill's scale runs the other way -
`TraceL3` is the least severe and `Critical` the most (`quill/core/LogLevel.h:26-44`). The
project's mapping between them (`include/cpp-core/logging/cib_quill.hpp:68-88`) sends cib's most
severe level to quill's least severe one, and cib's least severe level to quill's second-least
severe one:

| cib | quill | Severity, on quill's scale |
|---|---|---|
| `MAX` | `TraceL3` | **least severe** |
| `FATAL` | `Critical` | **most severe** |
| `ERROR` | `Error` | severe |
| `WARN` | `Warning` | - |
| `INFO` | `Info` | - |
| `USER1` | `Debug` | - |
| `USER2` | `TraceL1` | - |
| `TRACE` | `TraceL2` | second least severe |

The two ends are swapped, and the sink drops anything less severe than its threshold
(`quill/sinks/Sink.h:204`) - so with a sink at `Error`, a `MAX` message is dropped and a `FATAL`
message is kept. This is **`DEF-7`**, and part 20 has the evidence. Nothing misbehaves today,
because the project never logs at `MAX`.

**And the interface carries no function name.** `CIB_LOG` hands the customization point only
`__FILE__` and `__LINE__` (the `log/log.hpp:63-64` line above), so the catalog path cannot pass
one to quill - and passes an empty string instead
(`include/cpp-core/logging/cib_quill.hpp:157-159`). Part 6's option (e) fixes it.

### 2.3 Binary Logging (`logging::binary::`)

```cpp
// log_binary/catalog/catalog.hpp
namespace sc {
  template <typename...> struct args;
  template <char...> struct string {};
  template <typename, auto, auto> struct named_arg {};
  template <typename...> struct named_args;
  template <typename, typename> struct tag {};
  template <typename...> struct tags {};
  template <typename, auto, typename...> struct undefined;
  template <typename> struct message {};
  template <typename> struct module_string {};
}
using string_id = std::uint32_t;
using module_id = std::uint32_t;
template <typename> extern auto catalog() -> string_id;
template <typename> extern auto module() -> module_id;

// log_binary/encoder.hpp
namespace logging::binary {
  template <typename Destinations> struct log_writer { /* writes to destinations in critical section */ };
  template <typename Writer> struct log_handler {
    template <typename Env, typename FmtResult>
    auto log_msg(FmtResult const &fr) -> void;  // builds binary packet, writes via writer
    template <typename Env, auto Version, stdx::ct_string S = "">
    auto log_version() -> void;
  };
  template <typename... Dests> struct config {
    using destinations_tuple_t = stdx::tuple<Dests...>;
    constexpr explicit config(Dests... dests);
    log_handler<log_writer<destinations_tuple_t>> logger;
  };
}
```

### 2.4 Fmt-based Logging (`logging::fmt::`)

```cpp
// log_fmt/logger.hpp
namespace logging::fmt {
  template <logging::level L>
  constexpr std::string_view level_text = /* "MAX"/"FATAL"/... */;
  template <logging::level L>
  [[nodiscard]] constexpr auto format_as(level_wrapper<L>) -> std::string_view;

  template <typename TDestinations> struct log_handler {
    constexpr explicit log_handler(TDestinations &&ds);
    template <typename Env, typename FilenameStringType, typename LineNumberType, typename FmtResult>
    auto log(FilenameStringType, LineNumberType, FmtResult const &fr) -> void;  // uses fmt::format_to
  };

  template <typename... TDestinations> struct config {
    using destinations_tuple_t = stdx::tuple<TDestinations...>;
    constexpr explicit config(TDestinations... dests);
    log_handler<destinations_tuple_t> logger;
  };
}
```

---

## 3. Does the Binary Logger Have a Non-Macro Equivalent?

**No.** The `CIB_*` macros (`CIB_LOG`, `CIB_INFO`, `CIB_WARN`, `CIB_ERROR`, `CIB_TRACE`, `CIB_FATAL`, `CIB_ASSERT`) **do not have a non-macro, template-based equivalent** in the public API.

**Reason:** The macros exist to capture **three compile-time values simultaneously** that cannot be passed as template arguments to a function:

1. **`__FILE__`** — the source file name (string literal)
2. **`__LINE__`** — the source line number (integer)
3. **The format string** — as a compile-time `stdx::ct_string` via `STDX_CT_FORMAT(__VA_ARGS__)`

The macro expands to:
```cpp
logging::log<cib_log_env_t>(__FILE__, __LINE__, STDX_CT_FORMAT(__VA_ARGS__))
```
where `STDX_CT_FORMAT` is itself a macro that wraps the format string and arguments into a `stdx::ct_format` call, producing a `format_result` whose `.str` is a `ct_string` (the format string with compile-time arguments folded in) and `.args` is a tuple of runtime arguments.

A function template cannot capture `__FILE__` and `__LINE__` from the call site — those are **preprocessor-only** values. The macro is the *only* way to inject them into the type system. The `logging::log` function itself is a non-macro template, but it requires the caller to provide the file, line, and pre-formatted `format_result` — which in practice can only be constructed at the call site via the macro.

**Conclusion:** If you want the binary logging path (compile-time format string → string catalog ID → zero-overhead payload), you **must use the macros**. There is no macro-free API that achieves the same effect.

---

## 4. `intel-cpp-std-extensions` — What a C++26 Logging Project Would Want

| Facility | Header | `constexpr`-friendly? | Needs STL? | Relevance to Logging |
|----------|--------|----------------------|------------|---------------------|
| **`ct_string`** | `ct_string.hpp` | ✅ Fully | ❌ No | Format strings, module names, compile-time string manipulation |
| **`ct_format`** | `ct_format.hpp` | ✅ Fully | ❌ No (uses `fmt::formatted_size`/`format_to` at compile time via `__builtin_*`) | **Core compile-time formatting** — folds compile-time args into format string |
| **`tuple` / `tuple_algorithms`** | `tuple.hpp`, `tuple_algorithms.hpp` | ✅ Fully | ❌ No | Argument packs, heterogeneous collections, `apply`, `transform`, `for_each` |
| **`type_traits` (extended)** | `type_traits.hpp` | ✅ Fully | ❌ No | `to_underlying`, `is_cx_value_v`, `shrink/expand`, `nth_t`, `tuple_size_v` |
| **`env`** | `env.hpp` | ✅ Fully | ❌ No | Compile-time context propagation (level, module, tags, string_id) |
| **`bit`** | `bit.hpp` | ✅ Fully | ❌ No (falls back to `__builtin_*`) | Bit manipulation for packed binary log payloads |
| **`functional`** | `functional.hpp` | ✅ Fully | ❌ No | `overload`, `bind_front/back` for handler composition |
| **`span`** | `span.hpp` | ✅ Fully | ❌ No | Non-owning view over log buffers |
| **`optional`** | `optional.hpp` | ✅ Fully | ❌ No | Optional log fields |
| **`concepts`** | `concepts.hpp` | ✅ Fully | ❌ No (backports C++20) | Constrained templates for formatters/handlers |
| **`utility`** | `utility.hpp` | ✅ Mostly | ❌ No (except `type_map` uses `shrink/expand`) | `overload`, `forward_like`, `make_index_sequence`, `CX_VALUE`/`CT_WRAP` macros |
| **`panic`** | `panic.hpp` | ✅ Fully | ❌ No | Compile-time assertion / panic handler |
| **`atomic` / `atomic_bitset`** | `atomic.hpp`, `atomic_bitset.hpp` | ❌ No | ✅ Yes (`<atomic>`) | Thread-safe logging state |
| **`cached` / `call_by_need`** | `cached.hpp`, `call_by_need.hpp` | ✅ Fully | ❌ No | Lazy format string construction |
| **`intrusive_*_list`** | `intrusive_forward_list.hpp`, `intrusive_list.hpp` | ❌ No | ❌ No | Lock-free log queues (but not `constexpr`) |
| **`cx_map` / `cx_vector` / etc.** | `cx_*.hpp` | ✅ Fully | ❌ No | Compile-time catalogs (string ID assignment) |

**Key observation:** The `stdx::` facilities used by `intel-cib` logging (`ct_string`, `ct_format`, `tuple`, `type_traits`, `env`, `bit`, `functional`) are **all header-only, `constexpr`-friendly, and STL-free**. They are designed for compile-time computation and freestanding use.

---

## 5. Judgement: Could Any Replace Hand-Rolled Code?

### Project's Hand-Rolled Pieces (from `modules/logging/format.hpp` and related)

| Hand-Rolled Component | What It Does | Intel Equivalent? | Verdict |
|----------------------|--------------|-------------------|---------|
| **printf-style formatter** (`format_message`, `format_value`, `format_integer`, `format_double`, `parse_spec`, `scan_format`, `message_buffer`) | Full `std::format`-like runtime formatting with `{}` replacements, format specs (`{:>10}`, `{:x}`, `{:.2f}`), fixed 2048-byte stack buffer | `stdx::ct_format` is **compile-time only** — it produces a `format_result` with folded compile-time args and a tuple of runtime args. It does **not** do runtime formatting. `log_fmt/logger.hpp` delegates to `fmt::format_to` at runtime. | ❌ **Cannot replace**. The project's formatter is a *runtime* formatter. `stdx::ct_format` solves a different problem (compile-time folding). The project would still need a runtime formatter (or use `fmt`/`std::format` directly). |
| **Fixed-capacity message buffer** (`message_buffer` with 2048-byte stack array) | Stack-allocated buffer with `append`, `append_padded`, overflow protection | `stdx::span` + `stdx::array` could *implement* this, but no ready-made "fixed stack buffer with padding" type exists. `stdx::cx_vector` is compile-time only. | ⚠️ **Partial**. Could rebuild `message_buffer` using `stdx::array` + `stdx::span`, but no drop-in replacement. |
| **Quill level mapping** (`to_quill_level` in `cib_quill.hpp`) | Maps `logging::level` (MIPI Sys-T: MAX=0...TRACE=7) → `quill::LogLevel` (TraceL3...TraceL2) | No equivalent. This is project-specific. | ❌ **Cannot replace**. |
| **Float formatter** (`format_double` in `src/logging/quill_logger.cpp:121-167`) | Formats `double` with `type` (`f`/`e`/`g`) and `precision` into buffer | `stdx::ct_format` does **not** support runtime float formatting. `fmt`/`std::format` does, but that's external. | ❌ **Cannot replace**. (Read in full since this table was written - see section 7.) |

### What *Could* Be Adopted from Intel Libraries

| Project Need | Intel Facility | How It Helps |
|--------------|----------------|--------------|
| **Compile-time format string validation & arg counting** | `stdx::ct_format` + `num_fmt_specifiers` | Replace `scan_format`/`format_matches` with compile-time checks; catch mismatches at compile time |
| **Compile-time string manipulation** | `stdx::ct_string`, `shrink`, `operator""_cts` | Module names, format strings as template parameters |
| **Heterogeneous argument storage** | `stdx::tuple`, `tuple_algorithms::apply/transform/for_each` | Replace manual `formatter_fn[]` + `values[]` arrays with type-safe tuple operations |
| **Compile-time environment / context** | `stdx::env`, `extend_env_t` | Propagate log level, module, tags, string_id without runtime overhead |
| **Bit manipulation for binary payloads** | `stdx::bit` (all `constexpr`) | Pack/unpack binary log fields, `bit_mask`, `bit_destructure` |
| **Type reflection for catalog** | `stdx::ct_conversions::type_as_string`, `enum_as_string` | Generate catalog string IDs from types at compile time |
| **Critical section for log writes** | `conc::call_in_critical_section` | Replace manual mutex with policy-based critical section (but needs `std::mutex`) |
| **Sender/receiver async pipeline** | `async::` (full P2300) | If project moves to async logging, `just`, `then`, `sync_wait`, schedulers provide the machinery |

### What *Cannot* Be Replaced

- **Runtime formatting engine** — `stdx::ct_format` is compile-time only; the project needs runtime formatting for the module path (non-CIB macros).
- **Float formatting** — No `constexpr` float formatter in `stdx`; `fmt` or `std::format` required.
- **Quill integration** — Project-specific; no Intel equivalent.
- **Fixed stack buffer with padding logic** — Build from `stdx::array`/`span` but not provided.

---

## 6. License / Attribution Implications

All four Intel libraries are licensed under the **Boost Software License 1.0 (BSL-1.0)**.

### BSL-1.0 Requirements (from the copyright files)

> The copyright notices in the Software and this entire statement, including the above license grant, this restriction and the following disclaimer, **must be included in all copies of the Software, in whole or in part, and all derivative works of the Software, unless such copies or derivative works are solely in the form of machine-executable object code generated by a source language processor.**

### Implications for Vendoring (Copying Headers into the Project)

| Scenario | Requirement |
|----------|-------------|
| **Use via vcpkg (current)** | No action needed — headers remain in `vcpkg_installed`, license satisfied by binary distribution exception ("machine-executable object code"). |
| **Copy individual headers into project source tree** | **Must include** the BSL-1.0 license text **and** the original copyright notice in each copied file (or in a `LICENSE` file adjacent to them). The notice must appear "in all copies of the Software, in whole or in part." |
| **Modify headers before vendoring** | Derivative works also require the license notice. |
| **Only use templates/`constexpr` code that compiles into object code** | The exception applies: "unless such copies or derivative works are solely in the form of machine-executable object code generated by a source language processor." Since these are header-only templates, **the exception does not apply** — the source code *is* distributed (in headers), so the license notice must travel with it. |

### Practical Recommendation

If the project vendors any `intel-*` headers (e.g., copies `stdx/ct_format.hpp` or `stdx/tuple.hpp` into its own `include/`):

1. **Preserve the original license header** at the top of each file (it's already there in the installed headers).
2. **Add a `THIRD_PARTY_LICENSES` file** listing each vendored library, its version, and the BSL-1.0 text.
3. **Do not strip the copyright/license comments** from the headers.

The BSL-1.0 is permissive (similar to MIT/BSD) and allows commercial use, modification, and distribution — the only obligation is **attribution preservation**.

---

## 7. Unverified / Flagged Items

| Item | Status |
|------|--------|
| `stdx/algorithm.hpp`, `stdx/tuple_destructure.hpp`, `stdx/ranges.hpp`, `stdx/numeric.hpp`, `stdx/meta.hpp`, `stdx/cx_*.hpp`, `stdx/atomic_bitset.hpp` | Headers listed in `.list` but **not read** — functionality inferred from names and usage in other headers. |
| `intel-cib` flow/interrupt/msg/nexus/seq/lookup/match internals | Not analyzed — outside logging scope. |
| `async` schedulers (`runloop_scheduler`, `thread_scheduler`, etc.) | Headers listed but **not read** — assumed to implement P2300 scheduler concepts. |
| `log_binary/catalog/builder.hpp`, `mipi_builder.hpp`, `writer.hpp`, `arguments.hpp`, `mipi_messages.hpp` | Not read — encoder uses them but exact API not verified. |
| Project's `format_double` implementation | **Now read** (2026-11-12): the declaration is `include/cpp-core/logging/internal.hpp:52-53`, the definition is `src/logging/quill_logger.cpp:121-167`. It uses `std::snprintf` with `%f`, `%e`, `%E`, `%g` and `%G`, and treats `'f'` and the default alike (`quill_logger.cpp:131-137`). The verdict in section 5 stands, and the float default is **DEF-2** |
| `stdx::ct_format`'s implementation | **Now read** (2026-11-12): it is fmt's compile-time API - `STDX_FMT_COMPILE` is `FMT_COMPILE` (`stdx/detail/fmt.hpp:14`) and `perform_format` is a `consteval` that calls `fmt::format_to` into a fixed-size `ct_string` (`stdx/ct_format.hpp:326-331`). See [remaining-research.md](remaining-research.md) section 1 |
| `conc::atomic.hpp`, `conc::concepts.hpp` | Not read. |

---

## Summary

- **`intel-cib`** provides a **compile-time initialization framework** (`cib::top`, `nexus`, `config`) and **three logging backends** (null, binary, fmt). The **binary logger path requires macros** (`CIB_INFO`, etc.) — no macro-free equivalent exists because `__FILE__`/`__LINE__`/compile-time format string must be captured at the call site.
- **`intel-cpp-std-extensions` (`stdx::`)** is a **treasure trove of `constexpr`, STL-free utilities**: `ct_string`, `ct_format`, `tuple`, `env`, `bit`, `type_traits`, `functional`, `span`, `optional`, `concepts`. These **can replace or improve** the project's compile-time formatting validation, argument packing, context propagation, and bit manipulation.
- **`intel-baremetal-concurrency`** gives a **policy-based critical section** (`call_in_critical_section`) — usable but requires `std::mutex` (not `constexpr`).
- **`intel-baremetal-senders-and-receivers`** is a **complete P2300 sender/receiver implementation** with schedulers — relevant only if the project adopts async logging.
- **None of the Intel libraries replaces the project's runtime printf-style formatter, float formatter, fixed-capacity message buffer, or Quill level mapping.** They address the *compile-time* side; the runtime formatting remains the project's responsibility (or `fmt`/`std::format`).
- **All libraries are BSL-1.0** — vendoring headers requires preserving the license notice in each file.