#include <memory>
struct Holder { char *p; };
__attribute__((noinline)) static void leak() {
  auto h = std::make_unique<Holder>();
  h->p = new char[1234];
  h->p[0] = 1;
}
int main() { leak(); return 0; }
