// cpp-core: Intel's compile-time-init-build (cib) logging interface, implemented on top of quill.
//
// cib's logging is in two parts (https://github.com/intel/compile-time-init-build/blob/main/docs/logging.adoc):
// the interface in <log/log.hpp>, and an implementation selected by the application. This header
// provides that implementation, using quill as the logger.
//
// ODR note (from the cib docs): every translation unit that logs must see the same specialization
// of logging::config<>. A TU that does not include this header would use the null logger, so
// include it wherever CIB_* macros are used.

#pragma once

#include <log/log.hpp>
#include <log/module.hpp>

#include <stdx/ct_string.hpp>
#include <stdx/type_traits.hpp>
#include <stdx/utility.hpp>

#include <quill/Backend.h>
#include <quill/Frontend.h>
#include <quill/Logger.h>
#include <quill/core/LogLevel.h>
#include <quill/core/MacroMetadata.h>

#include <cstdint>
#include <string_view>
#include <type_traits>
#include <utility>

namespace cpp_core::logging {
namespace detail {

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

} // namespace detail

// The quill logger that cib's log calls are routed to. Starts quill's backend on first use.
[[nodiscard]] auto quill_logger() -> quill::Logger*;

// Starts quill's backend and creates the logger. Idempotent, and called automatically by the
// first log call if the application did not call it.
auto setup() -> void;

// Waits until the queued log messages have been written.
auto flush() -> void;

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

// The quill-backed implementation of cib's logging customization point.
//
// cib hands us the call site's file and line, the compile-time format string (with the
// compile-time arguments already folded into it) and the runtime arguments to interpolate. Quill
// formats on its backend thread, so the runtime arguments are queued rather than formatted here.
struct quill_config {
  struct {
    template <typename Env, typename File, typename Line, typename FR>
    auto log(File file, Line line, FR const &fr) const -> void {
      constexpr auto level = to_quill_level(detail::level_of(::logging::get_level(Env{})));

      // Both the format string and the module name have static storage duration, so the pointers
      // stay valid for as long as quill needs them.
      static constexpr auto fmtstr = std::string_view{decltype(fr.str)::value};
      static constexpr auto module = stdx::expand(::logging::get_module(Env{}));
      static constexpr std::string_view module_view{static_cast<std::string_view>(module)};

      // The placeholders are unused on the runtime-metadata path: the real file, line, format
      // string and tags are passed as arguments below.
      static constexpr quill::MacroMetadata metadata{"[placeholder]", "[placeholder]",
                                                    "[placeholder]", nullptr, quill::LogLevel::None,
                                                    quill::MacroMetadata::Event::
                                                        LogWithRuntimeMetadataDeepCopy};

      fr.args.apply([&]<typename... Args>(Args &&...args) {
        quill_logger()->template log_statement_runtime_metadata<true>(
            &metadata, fmtstr.data(), file, "", module_view.data(),
            static_cast<std::uint32_t>(line), level,
            detail::decay_enum_value(std::forward<Args>(args))...);
      });
    }
  } logger;
};

} // namespace cpp_core::logging

// Select the quill implementation for cib's logging. Every TU that logs must see this
// specialization (see the ODR note at the top of this header).
namespace logging {
template <>
inline auto config<> = cpp_core::logging::quill_config{};
} // namespace logging
