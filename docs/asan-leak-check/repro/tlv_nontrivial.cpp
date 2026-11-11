#include <cstdio>
#include <memory>
thread_local std::shared_ptr<int> x = std::make_shared<int>(7);
int main() { std::printf("%d\n", *x); return 0; }
