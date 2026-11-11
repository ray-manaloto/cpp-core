// cpp-core: the interface between the logging module and its implementation.
//
// The module's public interface deliberately avoids the standard library. A module's global
// module fragment is copied into every translation unit that imports it, so a standard header
// that the module's interface depends on would end up next to the standard headers of any
// translation unit that includes them, and the two copies collide:
//
//   GCC:    error: redefinition of 'constexpr bool std::__is_constant_evaluated()'
//   Clang:  error: type alias template redefinition with different types ('std::__promote_t')
//
// The module therefore reaches its implementation through this standard-library-free interface,
// and the implementation - a plain translation unit - is free to use the standard library and
// quill. This header is included both by the module (in its global module fragment, so that the
// module and the implementation share one set of declarations) and by the implementation.

#pragma once

namespace com::rsm::logging::detail {

// The severity levels, as plain integers: this interface cannot name the module's own enum,
// which lives in the module's purview.
inline constexpr int trace_level = 0;
inline constexpr int debug_level = 1;
inline constexpr int info_level = 2;
inline constexpr int warning_level = 3;
inline constexpr int error_level = 4;
inline constexpr int critical_level = 5;

// Starts the logger. Idempotent: the first log call starts it too.
auto start_logger() -> void;

// Waits until the queued log messages have been written.
auto flush_logger() -> void;

// Sets the least severe level that is logged.
auto set_log_level(int level) -> void;

// The least severe level that is logged.
[[nodiscard]] auto get_log_level() -> int;

// Hands a message to quill. The message is copied into quill's queue.
auto emit(int level, char const* message, unsigned long length) -> void;

// Formats a floating-point value into `out` (at most `capacity` bytes) and returns the number of
// bytes written. `type` is the format specifier's type character ('f', 'e', 'g', or '\0' for the
// default); `precision` is the number of digits after the decimal point, or -1 for the default.
auto format_double(double value, char type, int precision, char* out, unsigned long capacity)
    -> unsigned long;

} // namespace com::rsm::logging::detail
