// cpp-core: the application library.
//
// The log calls live here (and not in main.cpp), so that the string catalog tooling can scan the
// object files for the messages that need a catalog ID (see cmake/catalog.cmake).
//
// This is the catalog path: the format string and the compile-time arguments are compile-time
// values, the message is identified by a catalog ID, and only the runtime values go onto quill's
// queue.

#include <cpp-core/logging/cib_quill.hpp>

namespace demo {

// The C++26 static reflection demo. It is in its own translation unit, because the reflection
// header is not part of the standard library that the include-what-you-use checks use (see
// cmake/iwyu.cmake).
auto reflection_demo() -> void;

// CIB_LOG_MODULE declares cib_log_env_t in the enclosing namespace (it shadows the global alias
// of that name), so it goes inside a namespace rather than at global scope.
CIB_LOG_MODULE("cpp_core");

auto run() -> void {
  // A compile-time argument is folded into the format string at compile time; a runtime argument
  // is interpolated by quill on its backend thread. Either way, only the runtime values go onto
  // quill's queue.
  constexpr auto answer = 42;
  CIB_INFO("compile-time formatted: the answer is {}", answer);
  CIB_WARN("cib levels map onto quill levels: {}", "INFO -> Info, WARN -> Warning");
  CIB_ERROR("errors are logged too, at quill's Error level");

  reflection_demo();
}

} // namespace demo
