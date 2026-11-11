// cpp-core: the logging tests.
//
// The tests use ut (https://github.com/stephenberry/ut), the same way glaze does:
// a suite of tests, with the expectations checked by expect().
//
// The import comes first: an import declaration has to precede every other declaration of the
// translation unit.

import com.rsm.logging;

#include "ut/ut.hpp"

using namespace ut;

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
};

int main() {}
