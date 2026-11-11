// cpp-core reflection smoke.
// Verifies that the compiler, C++26 and the static-reflection flags (-freflection, and on
// clang-p2996 also -fexpansion-statements -fannotation-attributes) reach the build. ctest runs
// this executable as cpp-core-smoke; replace it once the real project takes shape.

#include <cstdio>
#include <meta>

struct point {
  int x = 1;
  int y = 2;
};

int main() {
  // GCC 16's member range cannot outlive constant evaluation, so call size() on the temporary.
  static_assert(
      std::meta::nonstatic_data_members_of(^^point, std::meta::access_context::unchecked()).size() == 2);
  std::puts("cpp-core: C++26 static reflection smoke OK (point has 2 data members)");
  return 0;
}
