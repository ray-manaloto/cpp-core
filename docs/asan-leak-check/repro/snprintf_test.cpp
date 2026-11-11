#include <cstdio>
int main() {
  char buf[64];
  std::snprintf(buf, sizeof(buf), "%f", 3.5);
  std::snprintf(buf, sizeof(buf), "%.*f", 2, 3.5);
  return buf[0] == '\0' ? 1 : 0;
}
