// Copyright 2024 cpp-core authors
//
// cpp-core: the logging tests.
//
// The tests use ut (https://github.com/stephenberry/ut), the same way glaze does:
// a suite of tests, with the expectations checked by expect().
//
// The import comes first: an import declaration has to precede every other declaration of the
// translation unit.

import com.rsm.logging;

#include "ut/ut.hpp"

#include <cstdio>
#include <string>
#include <unistd.h>

using namespace ut;

namespace {

// Captures what the logger writes to stdout, so that a test can look at it.
//
// The sink writes to the stdout stream, so the capture redirects the file descriptor of stdout to
// a temporary file and puts it back afterwards. The framework prints its summary at the very end,
// after every test has run, so nothing is lost.
class stdout_capture {
public:
  stdout_capture() : _file(std::tmpfile()), _saved_stdout(::dup(::fileno(stdout))) {
    if (_file != nullptr && _saved_stdout != -1) {
      // Whatever is still buffered belongs to the tests that ran before this one, so it is
      // written out before stdout is redirected.
      std::fflush(stdout);
      ::dup2(::fileno(_file), ::fileno(stdout));
    }
  }

  stdout_capture(stdout_capture const &) = delete;
  stdout_capture(stdout_capture &&) = delete;
  auto operator=(stdout_capture const &) -> stdout_capture & = delete;
  auto operator=(stdout_capture &&) -> stdout_capture & = delete;

  ~stdout_capture() {
    if (_saved_stdout != -1) {
      std::fflush(stdout);
      ::dup2(_saved_stdout, ::fileno(stdout));
      ::close(_saved_stdout);
    }
    if (_file != nullptr) {
      std::fclose(_file);
    }
  }

  [[nodiscard]] auto ok() const -> bool { return _file != nullptr && _saved_stdout != -1; }

  [[nodiscard]] auto contents() -> std::string {
    if (_file == nullptr) {
      return {};
    }
    std::fflush(stdout);
    std::rewind(_file);
    char buffer[4096];
    auto const read = std::fread(buffer, 1, sizeof(buffer) - 1, _file);
    return std::string{buffer, read};
  }

private:
  std::FILE *_file;
  int _saved_stdout;
};

} // namespace

suite tests = [] {
  "the level can be set and read back"_test = [] {
    com::rsm::logging::set_level(com::rsm::logging::level::warning);
    expect(com::rsm::logging::current_level() == com::rsm::logging::level::warning)
      << "the level was not changed";

    com::rsm::logging::set_level(com::rsm::logging::level::info);
    expect(com::rsm::logging::current_level() == com::rsm::logging::level::info);
  };

  "the levels are ordered from the least to the most severe"_test = [] {
    using com::rsm::logging::level;
    expect(static_cast<int>(level::trace) < static_cast<int>(level::debug));
    expect(static_cast<int>(level::debug) < static_cast<int>(level::info));
    expect(static_cast<int>(level::info) < static_cast<int>(level::warning));
    expect(static_cast<int>(level::warning) < static_cast<int>(level::error));
    expect(static_cast<int>(level::error) < static_cast<int>(level::critical));
  };

  "logging a message does not throw"_test = [] {
    com::rsm::logging::setup();
    com::rsm::logging::info("The answer is {}", 42);
    com::rsm::logging::warning("The answer is not {}", 42);
    com::rsm::logging::flush();
    expect(true) << "the logger should not have thrown";
  };

  "a message can be logged with every kind of value"_test = [] {
    com::rsm::logging::info("an integer: {}", 42);
    com::rsm::logging::info("a negative integer: {}", -42);
    com::rsm::logging::info("a boolean: {}", true);
    com::rsm::logging::info("a character: {}", 'x');
    com::rsm::logging::info("a double: {}", 3.5);
    com::rsm::logging::info("a string: {}", "hello");
    com::rsm::logging::info("several values: {} and {} and {}", 1, 2, 3);
    com::rsm::logging::info("an indexed value: {1} and {0}", "first", "second");
    com::rsm::logging::info("an escaped brace: {{}}");
    com::rsm::logging::flush();
    expect(true) << "the logger should not have thrown";
  };

  "a message that is already formatted can be logged"_test = [] {
    com::rsm::logging::log_raw(com::rsm::logging::level::info, "raw message", 11);
    com::rsm::logging::flush();
    expect(true) << "the logger should not have thrown";
  };

  "the format string is checked at compile time"_test = [] {
    // A format string that does not match its arguments does not compile, so the test can only
    // check that the well-formed ones work.
    com::rsm::logging::error("{} of {}", 1, 2);
    expect(true);
  };

  "a formatted log call carries the source location of the call"_test = [] {
    com::rsm::logging::set_level(com::rsm::logging::level::info);

    stdout_capture capture;
    expect(capture.ok()) << "could not capture stdout";

    auto const expected_line = __LINE__ + 1;
    com::rsm::logging::info("a message with a source location");
    com::rsm::logging::flush();

    // The location is the file and the line of the call above, not the ones of the module.
    auto const expected = "logging_test.cpp:" + std::to_string(expected_line) + " ";
    auto const output = capture.contents();
    expect(output.find(expected) != std::string::npos)
      << "the source location is not in the log output: " << output;
  };

  "a raw log call carries the source location of the call"_test = [] {
    com::rsm::logging::set_level(com::rsm::logging::level::info);

    stdout_capture capture;
    expect(capture.ok()) << "could not capture stdout";

    auto const expected_line = __LINE__ + 1;
    com::rsm::logging::log_raw(com::rsm::logging::level::info, "a raw message", 12);
    com::rsm::logging::flush();

    // The location is the file and the line of the call above, not the ones of the module.
    auto const expected = "logging_test.cpp:" + std::to_string(expected_line) + " ";
    auto const output = capture.contents();
    expect(output.find(expected) != std::string::npos)
      << "the source location is not in the log output: " << output;
  };
};

int main() {}
