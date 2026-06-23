#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/stat.h>
#include <dlfcn.h>
#include <unistd.h>

/*
 * HA add-on containers lack CAP_SETUID/CAP_SETGID, so we cannot drop to the
 * postgres OS user at runtime. postgres and initdb refuse to run as root
 * (geteuid()==0). This shim, loaded via LD_PRELOAD, overrides geteuid/getuid
 * to return 999 so postgres accepts the non-root check, and overrides the
 * stat family so the data-directory ownership check (st_uid == geteuid())
 * also passes. The process runs as actual root; files are root-owned.
 *
 * Loaded ONLY by postgres and initdb (see postgres/run and 00-init.sh).
 */

#define FAKE_UID ((uid_t)999)

uid_t geteuid(void) { return FAKE_UID; }
uid_t getuid(void)  { return FAKE_UID; }

static void patch_uid(struct stat *b) { if (b) b->st_uid = FAKE_UID; }

int stat(const char *p, struct stat *b) {
    static int (*real)(const char *, struct stat *);
    if (!real) real = dlsym(RTLD_NEXT, "stat");
    int r = real(p, b); if (!r) patch_uid(b); return r;
}
int fstat(int fd, struct stat *b) {
    static int (*real)(int, struct stat *);
    if (!real) real = dlsym(RTLD_NEXT, "fstat");
    int r = real(fd, b); if (!r) patch_uid(b); return r;
}
int lstat(const char *p, struct stat *b) {
    static int (*real)(const char *, struct stat *);
    if (!real) real = dlsym(RTLD_NEXT, "lstat");
    int r = real(p, b); if (!r) patch_uid(b); return r;
}
int fstatat(int d, const char *p, struct stat *b, int flags) {
    static int (*real)(int, const char *, struct stat *, int);
    if (!real) real = dlsym(RTLD_NEXT, "fstatat");
    int r = real(d, p, b, flags); if (!r) patch_uid(b); return r;
}
