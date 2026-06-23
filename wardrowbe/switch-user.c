#define _GNU_SOURCE
#include <sys/types.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

/*
 * Minimal user-switcher for HA containers (no CAP_SETGID).
 *
 * Usage: switch-user <uid> <gid> <program> [args...]
 *
 * Calls setgid(gid) + setuid(uid) — root can do this without CAP_SETGID —
 * then execvp(program, ...) so PATH is searched normally.
 * No getpwnam/getpwuid calls so the libfakeeuid.so shim doesn't interfere.
 *
 * Callers pass the numeric UID/GID of the data directory (stat -c '%u/%g')
 * so this works regardless of what UID the postgres OS user has in the
 * current image (which can differ between base image versions).
 */
int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "usage: switch-user <uid> <gid> <program> [args...]\n");
        return 1;
    }
    uid_t uid = (uid_t)strtoul(argv[1], NULL, 10);
    gid_t gid = (gid_t)strtoul(argv[2], NULL, 10);
    if (setgid(gid) < 0 || setuid(uid) < 0) {
        perror("switch-user");
        return 1;
    }
    execvp(argv[3], argv + 3);
    perror("switch-user: execvp");
    return 1;
}
