// cpp-core: the com.rsm.logging module.
//
// The module is the logging library's public interface:
//
//   import com.rsm.logging;
//
//   com::rsm::logging::info("The answer is {}", 42);
//
// The module's interface deliberately avoids the standard library. A module's global module
// fragment is copied into every translation unit that imports it, so a standard header that the
// module's interface depends on would end up next to the standard headers of any translation unit
// that includes them, and the two copies collide:
//
//   GCC:    error: redefinition of 'constexpr bool std::__is_constant_evaluated()'
//   Clang:  error: type alias template redefinition with different types ('std::__promote_t')
//
// The module therefore formats the messages itself (see format.hpp) and reaches its
// implementation - a plain translation unit that uses the standard library and quill - through
// the standard-library-free interface in cpp-core/logging/internal.hpp.
//
// The library also implements cib's logging interface (the CIB_* macros, see
// cpp-core/logging/cib_quill.hpp). That is the path that uses the string catalog: there the
// format string and the compile-time arguments are compile-time values, the message is
// identified by a catalog ID, and only the runtime values go onto quill's queue.

module;

#include <cpp-core/logging/internal.hpp>

export module com.rsm.logging;

// The module's private implementation.
#include "format.hpp"

export namespace com::rsm::logging {

// The severity of a log message, from the least to the most severe.
enum class level : unsigned char {
  trace = 0,
  debug = 1,
  info = 2,
  warning = 3,
  error = 4,
  critical = 5,
};

// A format string. The constructor is consteval, so the format string is checked at compile time:
// a format string that is malformed, or that does not match the number of arguments, does not
// compile.
//
// The template parameter is the list of the arguments, each of them wrapped in a type_identity so
// that the format string is not used to deduce them (see the log functions below).
template <typename... Wrapped>
class format_string {
public:
  template <unsigned long N>
  consteval format_string(char const (&text)[N]) : text(text), length(N - 1U) {
    if (!detail::format_matches<sizeof...(Wrapped)>(text, N - 1U)) {
      // A consteval function can only fail at compile time by throwing: the compiler reports the
      // throw at the call site.
      throw "the format string does not match the arguments";
    }
  }

  char const *text;
  unsigned long length;
};

// Starts the logging backend. Idempotent: the first log call starts it too.
auto setup() -> void { detail::start_logger(); }

// Waits until the queued log messages have been written.
auto flush() -> void { detail::flush_logger(); }

// Sets the least severe level that is logged.
auto set_level(level l) -> void { detail::set_log_level(static_cast<int>(l)); }

// The least severe level that is logged.
[[nodiscard]] auto current_level() -> level {
  return static_cast<level>(detail::get_log_level());
}

// Logs a message that is already formatted. It has its own name, so that it does not compete
// with the formatted overload below.
auto log_raw(level l, char const *message, unsigned long length) -> void {
  detail::emit(static_cast<int>(l), message, length);
}

// Logs a formatted message. The format string is checked at compile time: a format string that
// does not match the arguments does not compile.
template <typename... Args>
auto log(level l, format_string<detail::type_identity_t<Args>...> fmt, Args &&...args) -> void {
  detail::message_buffer buffer;
  detail::format_message(buffer, fmt.text, fmt.length, detail::forward<Args>(args)...);
  detail::emit(static_cast<int>(l), buffer.data(), buffer.size());
}

// Logs a message at the trace level.
template <typename... Args>
auto trace(format_string<detail::type_identity_t<Args>...> fmt, Args &&...args) -> void {
  log(level::trace, fmt, detail::forward<Args>(args)...);
}

// Logs a message at the debug level.
template <typename... Args>
auto debug(format_string<detail::type_identity_t<Args>...> fmt, Args &&...args) -> void {
  log(level::debug, fmt, detail::forward<Args>(args)...);
}

// Logs a message at the info level.
template <typename... Args>
auto info(format_string<detail::type_identity_t<Args>...> fmt, Args &&...args) -> void {
  log(level::info, fmt, detail::forward<Args>(args)...);
}

// Logs a message at the warning level.
template <typename... Args>
auto warning(format_string<detail::type_identity_t<Args>...> fmt, Args &&...args) -> void {
  log(level::warning, fmt, detail::forward<Args>(args)...);
}

// Logs a message at the error level.
template <typename... Args>
auto error(format_string<detail::type_identity_t<Args>...> fmt, Args &&...args) -> void {
  log(level::error, fmt, detail::forward<Args>(args)...);
}

// Logs a message at the critical level.
template <typename... Args>
auto critical(format_string<detail::type_identity_t<Args>...> fmt, Args &&...args) -> void {
  log(level::critical, fmt, detail::forward<Args>(args)...);
}

} // namespace com::rsm::logging
