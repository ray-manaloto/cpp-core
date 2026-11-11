#include <cstdio>
int main() {
  char buf[64];
  std::snprintf(buf, sizeof(buf), "%d", 42);
  return buf[0] == '\0' ? 1 : 0;
}
