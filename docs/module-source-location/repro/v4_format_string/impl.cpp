module demo;

#include <cstdio>

namespace com::rsm::logging {
template <typename... Args>
auto info(format_string<detail::type_identity_t<Args>...> fmt, Args &&...args) -> void {
  std::printf("file=%s line=%u function=%s text=%s\n", fmt.file, fmt.line, fmt.function, fmt.text);
}
template void info<int>(format_string<detail::type_identity_t<int>>, int &&);
} // namespace com::rsm::logging
