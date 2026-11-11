#include <cstdio>
#include <cstddef>
extern "C" int dyld_shared_cache_iterate_text(void (*callback)(const void *, size_t), void *ctx);
int main() {
  dyld_shared_cache_iterate_text([](const void *, size_t) {}, nullptr);
  std::printf("warmed\n");
  return 0;
}
