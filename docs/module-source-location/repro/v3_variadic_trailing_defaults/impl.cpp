module demo;

#include <cstdio>

namespace com::rsm::logging {
template <typename... Args> auto info(format_string<detail::type_identity_t<Args>...> fmt,
                                      Args &&...args, char const *file, unsigned line) -> void {
  std::printf("file=%s line=%u text=%s\n", file, line, fmt.text);
}
template void info<int>(format_string<detail::type_identity_t<int>>, int &&, char const *,
                        unsigned);
} // namespace com::rsm::logging
