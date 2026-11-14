#include <quill/Backend.h>
#include <quill/Frontend.h>
#include <quill/Logger.h>
#include <quill/core/MacroMetadata.h>
#include <quill/sinks/ConsoleSink.h>
#include <utility>
int main() {
  quill::Backend::start();
  auto sink = quill::Frontend::create_or_get_sink<quill::ConsoleSink>("s");
  auto *logger = quill::Frontend::create_or_get_logger("l", std::move(sink));
  static constexpr quill::MacroMetadata metadata{
    "f.cpp",
    "fn",
    "hello {}",
    nullptr,
    quill::LogLevel::None,
    quill::MacroMetadata::Event::LogWithRuntimeMetadataShallowCopy};
  logger->log_statement_runtime_metadata<true>(&metadata, "hello {}", "f.cpp", "fn", "", 1U,
                                               quill::LogLevel::Info, 42);
  logger->flush_log();
  return 0;
}
