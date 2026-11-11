#include <cpp-core/logging/cib_quill.hpp>

#include <quill/core/PatternFormatterOptions.h>
#include <quill/sinks/ConsoleSink.h>

#include <memory>
#include <utility>

namespace cpp_core::logging {
namespace {

constexpr auto logger_name = "cpp-core";
constexpr auto sink_id = "cpp-core-console";

// The pattern shows the cib module (a quill tag) next to the logger name.
constexpr auto pattern =
    "%(time) [%(thread_id)] %(short_source_location:<28) LOG_%(log_level:<9) %(logger:<12) "
    "[%(tags)] %(message)";

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

auto setup() -> void { (void)quill_logger(); }

auto flush() -> void {
  if (auto* logger = quill_logger(); logger != nullptr) {
    logger->flush_log();
  }
}

} // namespace cpp_core::logging
