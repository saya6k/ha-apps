#define _GNU_SOURCE
#include <pwd.h>
#include <sys/types.h>
#include <unistd.h>
#include <stdio.h>

/*
 * Minimal user-switcher: setgid()+setuid() without calling setgroups().
 *
 * HA containers lack CAP_SETGID, so setgroups() fails with EPERM.
 * s6-setuidgid (statically linked) calls setgroups() and therefore cannot
 * be used to drop privileges in HA containers.
 *
 * Root CAN call setgid()/setuid() to drop to a non-root user without
 * needing any extra capabilities.  The supplementary group list stays as
 * root's (effectively empty), which is acceptable for postgres data access.
 *
 * Usage: switch-user <username> <program> [args...]
 */
int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "usage: switch-user <username> <program> [args...]\n");
        return 1;
    }
    struct passwd *pw = getpwnam(argv[1]);
    if (!pw) {
        fprintf(stderr, "switch-user: unknown user: %s\n", argv[1]);
        return 1;
    }
    if (setgid(pw->pw_gid) < 0 || setuid(pw->pw_uid) < 0) {
        perror("switch-user");
        return 1;
    }
    execv(argv[2], argv + 2);
    perror("switch-user: execv");
    return 1;
}
