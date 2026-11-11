// cpp-core reflection smoke.
// Verifies that the compiler, C++26 and the static-reflection flags (-freflection, and on
// clang-p2996 also -fexpansion-statements -fannotation-attributes) reach the build, and that
// the quill dependency links and logs. ctest runs this executable as cpp-core-smoke; replace
// it once the real project takes shape.

#include <cstdio>
#include <meta>

#include "quill/LogMacros.h"
#include "quill/SimpleSetup.h"

struct point {
  int x = 1;
  int y = 2;
};

int main() {
  // GCC 16's member range cannot outlive constant evaluation, so call size() on the temporary.
  constexpr auto member_count =
      std::meta::nonstatic_data_members_of(^^point, std::meta::access_context::unchecked()).size();
  static_assert(member_count == 2);

  quill::Logger* logger = quill::simple_logger();
  LOG_INFO(logger, "cpp-core: C++26 static reflection OK (point has {} data members)", member_count);
  logger->flush_log();  // quill logs asynchronously; flush before exit
  return 0;
}
