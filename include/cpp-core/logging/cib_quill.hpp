// cpp-core: Intel's compile-time-init-build (cib) logging interface, implemented on top of quill.
//
// cib's logging is in two parts (https://github.com/intel/compile-time-init-build/blob/main/docs/logging.adoc):
// the interface in <log/log.hpp>, and an implementation selected by the application. This header
// provides that implementation, using quill as the logger.
//
// The implementation follows the "binary loggers" section of the cib documentation:
//
// - the format string and the compile-time arguments are compile-time values: cib folds the
//   compile-time arguments into the format string, and the format string becomes part of the
//   message's *type*, so no string data ends up in the payload;
// - each message and each module is identified by an ID from the string catalog, which the
//   gen_str_catalog() tooling assigns at build time (see cmake/ and the catalog target);
// - the payload that goes onto quill's queue is therefore only the metadata of the message
//   (the format string, the source location, the tags and the level - all of them compile-time
//   data, referenced rather than copied) plus the runtime values.
//
// ODR note (from the cib docs): every translation unit that logs must see the same specialization
// of logging::config<>. A TU that does not include this header would use the null logger, so
// include it wherever CIB_* macros are used.

#pragma once

#include <cpp-core/logging/quill_logger.hpp>

#include <log/log.hpp>
#include <log/module.hpp>
#include <log_binary/catalog/catalog.hpp>

#include <stdx/ct_string.hpp>
#include <stdx/type_traits.hpp>
#include <stdx/utility.hpp>

#include <quill/core/MacroMetadata.h>

#include <cstdint>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>

namespace com::rsm::logging::detail {

// The level query returns either the level itself or a wrapper holding it; accept both shapes.
template <typename T> [[nodiscard]] constexpr auto level_of(T &&t) noexcept {
  if constexpr (requires { t.value; }) {
    return t.value;
  } else {
    return t;
  }
}

// fmt (and therefore quill) cannot format a scoped enum that has no formatter of its own; cib's
// fmt logger decays enums to their underlying type for the same reason.
template <typename T> [[nodiscard]] auto decay_enum_value(T const &t) -> decltype(auto) {
  if constexpr (requires { format_as(t); } or not std::is_enum_v<T>) {
    return (t);
  } else {
    return stdx::to_underlying(t);
  }
}

// cib's levels follow the MIPI Sys-T severity scale (0 = most severe, 7 = most verbose); quill's
// scale runs the other way (higher = more severe). This mapping preserves the relative order:
//
//   cib:    MAX  FATAL  ERROR  WARN  INFO  USER1  USER2  TRACE
//   quill:  TrL3  Crit   Error  Warn  Info  Debug  TrL1   TrL2
[[nodiscard]] constexpr auto to_quill_level(::logging::level l) noexcept -> quill::LogLevel {
  switch (l) {
  case ::logging::level::MAX:
    return quill::LogLevel::TraceL3;
  case ::logging::level::FATAL:
    return quill::LogLevel::Critical;
  case ::logging::level::ERROR:
    return quill::LogLevel::Error;
  case ::logging::level::WARN:
    return quill::LogLevel::Warning;
  case ::logging::level::INFO:
    return quill::LogLevel::Info;
  case ::logging::level::USER1:
    return quill::LogLevel::Debug;
  case ::logging::level::USER2:
    return quill::LogLevel::TraceL1;
  case ::logging::level::TRACE:
    return quill::LogLevel::TraceL2;
  }
  return quill::LogLevel::Info;
}

// The catalog's string type: the characters of a compile-time string become template arguments,
// so the string is part of the type and not of the data (this is what keeps the string data out
// of the binary).
template <typename Str> [[nodiscard]] consteval auto string_type() {
  // Str is a stdx::cts_t: its value is the compile-time string, whose characters are the array
  // (the last one being the terminating null).
  constexpr auto &chars = Str::value.value;
  return [&]<std::size_t... Is>(std::index_sequence<Is...>) {
    return sc::string<chars[Is]...>{};
  }(std::make_index_sequence<chars.size() - 1U>{});
}

// The catalog's message type: the format string and the types of the runtime arguments. The
// catalog tooling assigns a string ID to each distinct type.
template <typename Str, typename... Args>
using message_type_t = sc::message<sc::undefined<sc::args<Args...>, -1, decltype(string_type<Str>()),
                                                sc::tags<>, sc::named_args<>>>;

// The catalog's string type for a module name.
template <typename Env> [[nodiscard]] consteval auto module_string_type() {
  // The module name is a compile-time value; it is kept in a static so that the characters have
  // static storage duration (a string_view of a temporary would not be a constant expression).
  static constexpr auto module = stdx::expand(::logging::get_module(Env{}));
  constexpr auto &chars = module.value;
  return [&]<std::size_t... Is>(std::index_sequence<Is...>) {
    return sc::string<chars[Is]...>{};
  }(std::make_index_sequence<chars.size() - 1U>{});
}

// The catalog's module type.
template <typename Env>
using module_type_t = sc::module_string<sc::undefined<void, -1, decltype(module_string_type<Env>())>>;

// The quill-backed implementation of cib's logging customization point.
//
// cib hands us the call site's file and line, the compile-time format string (with the
// compile-time arguments already folded into it) and the runtime arguments to interpolate. Quill
// formats on its backend thread, so the runtime arguments are queued rather than formatted here.
struct quill_config {
  struct {
    template <typename Env, typename File, typename Line, typename FR>
    auto log(File file, Line line, FR const &fr) const -> void {
      constexpr auto level = to_quill_level(level_of(::logging::get_level(Env{})));

      fr.args.apply([&]<typename... Args>(Args &&...args) {
        using Message = message_type_t<decltype(fr.str), std::remove_cvref_t<Args>...>;
        using Module = module_type_t<Env>;

        // The catalog IDs. They are assigned at build time by the gen_str_catalog() tooling and
        // are the only identification of the message that goes onto the queue.
        auto const string_id = ::catalog<Message>();
        auto const module_id = ::module<Module>();

        // Compile-time data, built once per message type and then referenced (never copied) by
        // the messages that use it.
        static constexpr auto module = stdx::expand(::logging::get_module(Env{}));
        static constexpr std::string_view module_name{static_cast<std::string_view>(module)};
        static const auto fmt = std::string{std::string_view{decltype(fr.str)::value}};
        static const auto tags = std::string{module_name} + " id=" + std::to_string(string_id) +
                                 " mod=" + std::to_string(module_id);

        // The metadata of the statement. The placeholders are unused on the runtime-metadata
        // path: the real file, line, format string and tags are passed as arguments below.
        static constexpr quill::MacroMetadata metadata{
            "[placeholder]", "[placeholder]", "[placeholder]", nullptr, quill::LogLevel::None,
            quill::MacroMetadata::Event::LogWithRuntimeMetadataShallowCopy};

        quill_logger()->template log_statement_runtime_metadata<true>(
            &metadata, fmt.c_str(), file, "", tags.c_str(), static_cast<std::uint32_t>(line), level,
            decay_enum_value(std::forward<Args>(args))...);
      });
    }
  } logger;
};

} // namespace com::rsm::logging::detail

// Select the quill implementation for cib's logging. Every TU that logs must see this
// specialization (see the ODR note at the top of this header).
namespace logging {
template <>
inline auto config<> = com::rsm::logging::detail::quill_config{};
} // namespace logging
