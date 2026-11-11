// cpp-core: the quill logger that backs the logging library.
//
// Quill formats on its backend thread, so the messages are queued and written asynchronously.
// The logger is created on first use and shared by every logging path.
//
// This is a plain translation unit, not part of the logging module: it is the one place where
// the standard library and quill are used, and the module reaches it through the
// standard-library-free interface in cpp-core/logging/internal.hpp.

#include <cpp-core/logging/internal.hpp>
#include <cpp-core/logging/quill_logger.hpp>

#include <quill/Backend.h>
#include <quill/Frontend.h>
#include <quill/Logger.h>
#include <quill/core/LogLevel.h>
#include <quill/core/MacroMetadata.h>
#include <quill/core/PatternFormatterOptions.h>
#include <quill/sinks/ConsoleSink.h>

#include <cstdio>
#include <memory>
#include <string>
#include <utility>

namespace com::rsm::logging::detail {
namespace {

constexpr auto logger_name = "cpp-core";
constexpr auto sink_id = "cpp-core-console";

// The pattern shows the tags (the cib module and the catalog IDs) next to the logger name.
constexpr auto pattern =
    "%(time) [%(thread_id)] %(short_source_location:<28) LOG_%(log_level:<9) %(logger:<12) "
    "[%(tags)] %(message)";

[[nodiscard]] auto to_quill_level(int level) -> quill::LogLevel {
  switch (level) {
  case trace_level:
    return quill::LogLevel::TraceL2;
  case debug_level:
    return quill::LogLevel::Debug;
  case info_level:
    return quill::LogLevel::Info;
  case warning_level:
    return quill::LogLevel::Warning;
  case error_level:
    return quill::LogLevel::Error;
  case critical_level:
    return quill::LogLevel::Critical;
  default:
    break;
  }
  return quill::LogLevel::Info;
}

[[nodiscard]] auto from_quill_level(quill::LogLevel level) -> int {
  switch (level) {
  case quill::LogLevel::TraceL3:
  case quill::LogLevel::TraceL2:
  case quill::LogLevel::TraceL1:
    return trace_level;
  case quill::LogLevel::Debug:
    return debug_level;
  case quill::LogLevel::Notice:
  case quill::LogLevel::Info:
    return info_level;
  case quill::LogLevel::Warning:
    return warning_level;
  case quill::LogLevel::Error:
    return error_level;
  case quill::LogLevel::Critical:
    return critical_level;
  case quill::LogLevel::Backtrace:
  case quill::LogLevel::None:
    break;
  }
  return info_level;
}

} // namespace

auto quill_logger() -> quill::Logger* {
  static quill::Logger* logger = []() -> quill::Logger* {
    quill::Backend::start();
    auto sink = quill::Frontend::create_or_get_sink<quill::ConsoleSink>(sink_id);
    return quill::Frontend::create_or_get_logger(logger_name, std::move(sink),
                                                 quill::PatternFormatterOptions{pattern});
  }();
  return logger;
}

auto start_logger() -> void { (void)quill_logger(); }

auto flush_logger() -> void {
  if (auto* logger = quill_logger(); logger != nullptr) {
    logger->flush_log();
  }
}

auto set_log_level(int level) -> void { quill_logger()->set_log_level(to_quill_level(level)); }

auto get_log_level() -> int { return from_quill_level(quill_logger()->get_log_level()); }

auto emit(int level, char const* file, unsigned line, char const* function, char const* message,
          unsigned long length) -> void {
  // The message is already formatted, so the format string of the statement is "{}" and the
  // message itself is the only value that goes onto the queue.
  static constexpr quill::MacroMetadata metadata{
      "[cpp-core]", "[cpp-core]", "{}", nullptr, quill::LogLevel::None,
      quill::MacroMetadata::Event::LogWithRuntimeMetadataShallowCopy};

  quill_logger()->template log_statement_runtime_metadata<true>(
      &metadata, "{}", file, function, "", line, to_quill_level(level),
      std::string{message, length});
}

auto format_double(double value, char type, int precision, char* out, unsigned long capacity)
    -> unsigned long {
  if (capacity == 0U) {
    return 0U;
  }

  // snprintf writes at most capacity - 1 characters and always null-terminates. The format
  // string is spelled out for every case, so that the compiler can check it.
  int written = 0;
  switch (type) {
  case 'f':
  case '\0':
    // The default type is the shortest representation, unless a precision is given: then the
    // precision is the number of digits after the decimal point, as in std::format.
    written = precision >= 0 ? std::snprintf(out, capacity, "%.*f", precision, value)
                             : std::snprintf(out, capacity, "%g", value);
    break;
  case 'e':
    written = precision >= 0 ? std::snprintf(out, capacity, "%.*e", precision, value)
                             : std::snprintf(out, capacity, "%e", value);
    break;
  case 'E':
    written = precision >= 0 ? std::snprintf(out, capacity, "%.*E", precision, value)
                             : std::snprintf(out, capacity, "%E", value);
    break;
  case 'G':
    written = precision >= 0 ? std::snprintf(out, capacity, "%.*G", precision, value)
                             : std::snprintf(out, capacity, "%G", value);
    break;
  case 'g':
  default:
    written = precision >= 0 ? std::snprintf(out, capacity, "%.*g", precision, value)
                             : std::snprintf(out, capacity, "%g", value);
    break;
  }

  if (written < 0) {
    out[0] = '\0';
    return 0U;
  }
  auto const length = static_cast<unsigned long>(written);
  if (length >= capacity) {
    // The output was truncated: report what actually fits.
    return capacity - 1U;
  }
  return length;
}

} // namespace com::rsm::logging::detail
