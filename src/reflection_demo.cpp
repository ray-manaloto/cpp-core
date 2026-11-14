// Copyright 2024 cpp-core authors
//
// cpp-core: the C++26 static reflection demo.
//
// It is in its own translation unit, because the reflection header is not part of the standard
// library that the include-what-you-use checks use (see cmake/iwyu.cmake): those checks run with
// the Homebrew toolchain, whose standard library has no reflection header yet.
//
// This is also the module path: the message is formatted by the logging module, whose interface
// is imported - none of the logging machinery is included.

import com.rsm.logging;

#include <meta>

namespace demo {

struct point {
  int x = 1;
  int y = 2;
};

auto reflection_demo() -> void {
  // GCC 16's member range cannot outlive constant evaluation, so call size() on the temporary.
  constexpr auto member_count =
    std::meta::nonstatic_data_members_of(^^point, std::meta::access_context::unchecked()).size();
  static_assert(member_count == 2);

  com::rsm::logging::info("cpp-core: C++26 static reflection OK (point has {} data members)",
                          member_count);
}

} // namespace demo
