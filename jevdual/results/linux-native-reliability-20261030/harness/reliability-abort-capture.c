#include <signal.h>
#include <unistd.h>
static void stop_on_abort(int sig) {
    const char message[] = "[diagnostic] actual SIGABRT: stopping for native stack capture\n";
    write(2, message, sizeof(message)-1);
    kill(getpid(), SIGSTOP);
    struct sigaction action = {0};
    action.sa_handler = SIG_DFL;
    sigemptyset(&action.sa_mask);
    sigaction(sig, &action, 0);
    /* libc abort restores and raises SIGABRT after this handler returns. */
}
__attribute__((constructor)) static void install(void) {
    struct sigaction action = {0};
    action.sa_handler = stop_on_abort;
    sigemptyset(&action.sa_mask);
    sigaction(SIGABRT, &action, 0);
}
