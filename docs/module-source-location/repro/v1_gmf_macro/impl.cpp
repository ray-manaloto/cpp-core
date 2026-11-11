module demo;

#include <cstdio>

namespace com::rsm::logging {
auto info(int value) -> void { std::printf("value=%d\n", value); }
} // namespace com::rsm::logging
