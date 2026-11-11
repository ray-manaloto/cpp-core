#include <cstdio>
#include <cstdlib>
#include <sys/wait.h>
#include <unistd.h>
#include <csignal>
extern "C" int __lsan_do_recoverable_leak_check();
int main() {
  auto *p = static_cast<char *>(std::malloc(4321)); // deliberate leak in the parent
  p[0] = 1;
  pid_t pid = fork();
  if (pid == 0) { int rc = __lsan_do_recoverable_leak_check(); _exit(rc == 0 ? 0 : 1); }
  int status = 0;
  for (int i = 0; i < 50; ++i) { if (waitpid(pid, &status, WNOHANG) == pid) { std::printf("child done\n"); return 0; } usleep(100000); }
  kill(pid, SIGKILL); waitpid(pid, &status, 0); std::printf("child hung\n"); return 0;
}
