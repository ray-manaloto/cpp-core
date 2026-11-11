// cpp-core reflection smoke.
// Verifies that the compiler, C++26 and the static-reflection flags (-freflection, and on
// clang-p2996 also -fexpansion-statements -fannotation-attributes) reach the build, and that
// the logging stack (cib's logging interface with quill as the logger) works. ctest runs this
// executable as cpp-core-smoke; replace it once the real project takes shape.

#include <cpp-core/logging/cib_quill.hpp>

#include <cstdio>
#include <meta>

struct point {
  int x = 1;
  int y = 2;
};

// CIB_LOG_MODULE declares cib_log_env_t in the enclosing namespace (it shadows the global alias
// of that name), so it goes inside a namespace rather than at global scope.
namespace demo {

CIB_LOG_MODULE("cpp_core");

auto log_reflection_smoke(int member_count) -> void {
  constexpr auto answer = 42;
  // A compile-time argument is folded into the format string at compile time; a runtime argument
  // is interpolated by quill on its backend thread.
  CIB_INFO("compile-time formatted: the answer is {}", answer);
  CIB_INFO("cpp-core: C++26 static reflection OK (point has {} data members)", member_count);
  CIB_WARN("cib levels map onto quill levels: {}", "INFO -> Info, WARN -> Warning");
  CIB_ERROR("errors are logged too, at quill's Error level");
}

} // namespace demo

int main() {
  // GCC 16's member range cannot outlive constant evaluation, so call size() on the temporary.
  constexpr auto member_count =
      std::meta::nonstatic_data_members_of(^^point, std::meta::access_context::unchecked()).size();
  static_assert(member_count == 2);

  cpp_core::logging::setup();
  demo::log_reflection_smoke(static_cast<int>(member_count));
  cpp_core::logging::flush();
  return 0;
}
