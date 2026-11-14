#include <cstdio>
thread_local int x = 7;
int main() {
  std::printf("%d\n", x);
  return 0;
}
