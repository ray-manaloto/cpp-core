#include <cstdio>
extern "C" int __lsan_do_recoverable_leak_check();
int main() {
  std::printf("checking early: %d\n", __lsan_do_recoverable_leak_check());
  return 0;
}
