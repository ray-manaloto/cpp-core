// Does running the leak check in a forked child work under ASan?
#include <cstdio>
#include <cstdlib>
#include <sys/wait.h>
#include <unistd.h>
#include <csignal>
extern "C" int __lsan_do_recoverable_leak_check();
int main() {
  pid_t pid = fork();
  if (pid == 0) {
    int rc = __lsan_do_recoverable_leak_check();
    _exit(rc == 0 ? 0 : 1);
  }
  // Parent: wait with a 5 s timeout, then kill.
  int status = 0;
  for (int i = 0; i < 50; ++i) {
    pid_t r = waitpid(pid, &status, WNOHANG);
    if (r == pid) {
      std::printf("child finished, status=%d\n", status);
      return 0;
    }
    usleep(100000);
  }
  std::printf("child still running after 5s -> killing\n");
  kill(pid, SIGKILL);
  waitpid(pid, &status, 0);
  return 0;
}
