#include <cstdlib>
int main() { auto *p = static_cast<char *>(std::malloc(1234)); p[0] = 1; return 0; } // deliberate leak
